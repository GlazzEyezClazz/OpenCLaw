"""
Основной движок парсера.
Автоматически выбирает стратегию: httpx → cloudscraper → playwright.
Поддерживает ротацию прокси.
"""
import asyncio
import logging
import random
from typing import Optional
from urllib.parse import urlparse, urlencode, quote_plus

from .strategies.base import FetchResult
from .strategies.requests_strategy import RequestsStrategy
from .strategies.cloudscraper_strategy import CloudscraperStrategy
from .strategies.playwright_strategy import PlaywrightStrategy
from .extractor import get_extractor
from config import settings

logger = logging.getLogger(__name__)

# Порядок стратегий: от быстрой к мощной
STRATEGY_CHAIN = [
    RequestsStrategy(),
    CloudscraperStrategy(),
    PlaywrightStrategy(),
]

# Поисковые шаблоны для нахождения товара на сайте
SEARCH_TEMPLATES = {
    "default": "{base_url}/search?q={query}",
    "wildberries.ru": "https://www.wildberries.ru/catalog/0/search.aspx?search={query}",
    "ozon.ru": "https://www.ozon.ru/search/?text={query}",
    "avito.ru": "https://www.avito.ru/rossiya?q={query}",
    "aliexpress.ru": "https://aliexpress.ru/wholesale?SearchText={query}",
    "market.yandex.ru": "https://market.yandex.ru/search?text={query}",
    "dns-shop.ru": "https://www.dns-shop.ru/search/?q={query}",
    "mvideo.ru": "https://www.mvideo.ru/byt-texnika/search?q={query}",
    "eldorado.ru": "https://www.eldorado.ru/search/catalog.php?q={query}",
    "amazon.com": "https://www.amazon.com/s?k={query}",
    "ebay.com": "https://www.ebay.com/sch/i.html?_nkw={query}",
}


def _get_search_url(site: str, query: str) -> str:
    """Формируем URL поиска для сайта."""
    # Нормализуем домен
    domain = site.replace("https://", "").replace("http://", "").split("/")[0].lower()
    encoded = quote_plus(query)

    for known_domain, template in SEARCH_TEMPLATES.items():
        if known_domain in domain:
            return template.format(query=encoded)

    # Для неизвестных сайтов пробуем стандартный ?q= или ?search=
    base = site if site.startswith("http") else f"https://{site}"
    return f"{base}/search?q={encoded}&search={encoded}"


def _pick_proxy(proxies: list[str]) -> Optional[str]:
    """Случайный прокси из списка."""
    if not proxies:
        return None
    return random.choice(proxies)


class ScraperEngine:
    """
    Универсальный движок парсинга.

    Для каждого URL пробует стратегии по цепочке:
    1. httpx (быстро, без JS)
    2. cloudscraper (Cloudflare bypass без браузера)
    3. playwright stealth (полный браузер, обходит всё)
    """

    def __init__(self, options: Optional[dict] = None):
        self.options = options or {}
        self.proxies = self._load_proxies()
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_tasks)

    def _load_proxies(self) -> list[str]:
        # Прокси из опций запроса имеют приоритет над .env
        if self.options.get("proxies"):
            return self.options["proxies"]
        return settings.proxies

    async def fetch_with_fallback(self, url: str, js_render: str = "auto") -> FetchResult:
        """
        Загружает URL с автоматическим выбором стратегии.

        js_render:
          "never"  — только httpx (быстро)
          "always" — сразу playwright (медленно, но надёжно)
          "auto"   — пробует по цепочке, переключается при блокировке
        """
        proxy = _pick_proxy(self.proxies)
        timeout = self.options.get("timeout", settings.default_timeout)

        if js_render == "never":
            strategies = STRATEGY_CHAIN[:1]
        elif js_render == "always":
            strategies = STRATEGY_CHAIN[2:]
        else:
            strategies = STRATEGY_CHAIN

        last_result = None
        for strategy in strategies:
            logger.info(f"[{strategy.name}] Загружаю: {url}")
            result = await strategy.fetch(url, proxy=proxy, timeout=timeout)

            if result.success:
                logger.info(f"[{strategy.name}] Успех: {url} ({result.status_code})")
                return result

            logger.warning(f"[{strategy.name}] Не удалось: {result.error} — пробую следующую стратегию")
            last_result = result

        # Все стратегии провалились
        return last_result or FetchResult(
            html="", url=url, status_code=0,
            strategy_used="none", error="all strategies failed"
        )

    async def scrape_site(self, product: str, site: str, fields: list[str]) -> dict:
        """Парсит один сайт: поиск товара → сбор данных."""
        async with self.semaphore:
            js_render = self.options.get("js_render", "auto")

            # Шаг 1: Получаем страницу поиска
            search_url = _get_search_url(site, product)
            logger.info(f"Поиск товара '{product}' на {site}: {search_url}")

            search_result = await self.fetch_with_fallback(search_url, js_render)

            if not search_result.success:
                return {
                    "site": site,
                    "product": product,
                    "status": "error",
                    "error": f"Не удалось загрузить страницу поиска: {search_result.error}",
                    "strategy_used": search_result.strategy_used,
                }

            # Шаг 2: Claude извлекает данные (ссылки на карточки + данные с выдачи)
            extractor = get_extractor()
            extracted = extractor.extract(
                html=search_result.html,
                url=search_result.url,
                product_name=product,
                fields=fields,
            )

            # Шаг 3: Если нашли карточку товара — заходим и собираем полные данные
            page_type = extracted.get("page_type", "other")
            product_url = extracted.get("product_url") or (
                extracted.get("items", [{}])[0].get("product_url") if extracted.get("items") else None
            )

            if page_type in ("catalog", "search_results") and product_url:
                logger.info(f"Переходим на карточку товара: {product_url}")
                await asyncio.sleep(random.uniform(1, 2))  # human delay

                card_result = await self.fetch_with_fallback(product_url, js_render)
                if card_result.success:
                    card_data = extractor.extract(
                        html=card_result.html,
                        url=card_result.url,
                        product_name=product,
                        fields=fields,
                    )
                    extracted.update(card_data)
                    extracted["product_url"] = card_result.url

            return {
                "site": site,
                "product": product,
                "status": "ok",
                "strategy_used": search_result.strategy_used,
                "search_url": search_result.url,
                **extracted,
            }

    async def run(self, tasks: list[dict]) -> list[dict]:
        """Запускает все задачи параллельно (с учётом semaphore)."""
        coroutines = []
        for task in tasks:
            product = task["product"]
            fields = task.get("extract", ["price", "currency", "product_url", "seller", "availability"])
            for site in task.get("sites", []):
                coroutines.append(self.scrape_site(product, site, fields))

        results = await asyncio.gather(*coroutines, return_exceptions=True)

        output = []
        for r in results:
            if isinstance(r, Exception):
                output.append({"status": "error", "error": str(r)})
            else:
                output.append(r)

        return output
