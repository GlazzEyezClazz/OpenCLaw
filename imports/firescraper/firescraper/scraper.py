"""
Ядро скрейпера — Playwright + умное извлечение данных.
Именно здесь магия: рендеринг JS, обход anti-bot, извлечение цен.
"""

import asyncio
import re
import json
import random
from typing import Optional
from urllib.parse import urlencode, quote_plus

from playwright.async_api import async_playwright, Page, BrowserContext
from bs4 import BeautifulSoup


# ── Anti-bot: реалистичные параметры браузера ──────────────────────────────────

BROWSER_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-blink-features=AutomationControlled",  # скрываем что мы бот
    "--disable-infobars",
    "--disable-dev-shm-usage",
    "--no-first-run",
    "--disable-extensions",
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
    {"width": 1280, "height": 800},
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
]


async def _make_context(playwright, proxy: Optional[str] = None) -> tuple:
    """Создаёт браузерный контекст с anti-bot настройками"""
    browser_kwargs = {
        "args": BROWSER_ARGS,
        "headless": True,
    }
    if proxy:
        # proxy format: "http://user:pass@host:port"
        proxy_parts = re.match(r"(?:https?://)?(?:([^:]+):([^@]+)@)?([^:]+):(\d+)", proxy)
        if proxy_parts:
            user, pwd, host, port = proxy_parts.groups()
            browser_kwargs["proxy"] = {
                "server": f"http://{host}:{port}",
                **({"username": user, "password": pwd} if user else {})
            }

    browser = await playwright.chromium.launch(**browser_kwargs)

    ua = random.choice(USER_AGENTS)
    vp = random.choice(VIEWPORTS)

    context = await browser.new_context(
        user_agent=ua,
        viewport=vp,
        locale="ru-RU",
        timezone_id="Europe/Moscow",
        # Скрываем webdriver флаги
        extra_http_headers={
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
        }
    )

    # Патчим navigator.webdriver — главный признак бота
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['ru-RU', 'ru', 'en-US'] });
        window.chrome = { runtime: {} };
    """)

    return browser, context


async def _wait_and_get_content(page: Page, wait_for: Optional[str], timeout: int) -> str:
    """Ждёт загрузки страницы и возвращает HTML"""
    try:
        await page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception:
        await page.wait_for_load_state("domcontentloaded", timeout=timeout)

    # Ждём конкретный элемент если указан
    if wait_for:
        try:
            await page.wait_for_selector(wait_for, timeout=10000)
        except Exception:
            pass  # не критично, продолжаем

    # Скроллим страницу — некоторые сайты подгружают данные при скролле
    await page.evaluate("""
        async () => {
            await new Promise(resolve => {
                let totalHeight = 0;
                const distance = 300;
                const timer = setInterval(() => {
                    window.scrollBy(0, distance);
                    totalHeight += distance;
                    if (totalHeight >= Math.min(document.body.scrollHeight, 3000)) {
                        clearInterval(timer);
                        resolve();
                    }
                }, 100);
            });
        }
    """)

    return await page.content()


def _html_to_markdown(html: str) -> str:
    """Конвертирует HTML в чистый Markdown — как делает Firecrawl"""
    soup = BeautifulSoup(html, "html.parser")

    # Убираем мусор
    for tag in soup(["script", "style", "nav", "footer", "iframe",
                     "noscript", "svg", "header", "aside", "ads"]):
        tag.decompose()

    # Конвертируем основные теги
    lines = []
    for elem in soup.find_all(["h1","h2","h3","h4","p","li","a","img","table","tr","td","th"]):
        text = elem.get_text(separator=" ", strip=True)
        if not text:
            continue
        tag = elem.name
        if tag == "h1":
            lines.append(f"# {text}")
        elif tag == "h2":
            lines.append(f"## {text}")
        elif tag == "h3":
            lines.append(f"### {text}")
        elif tag in ("h4","h5","h6"):
            lines.append(f"#### {text}")
        elif tag == "p":
            lines.append(text)
        elif tag == "li":
            lines.append(f"- {text}")
        elif tag == "a":
            href = elem.get("href","")
            if href and text:
                lines.append(f"[{text}]({href})")
        elif tag in ("td","th"):
            lines.append(f"| {text} |")

    return "\n\n".join(dict.fromkeys(lines))  # убираем дубли, сохраняем порядок


def _extract_structured_data(html: str, url: str) -> dict:
    """
    Умное извлечение цены, наличия, продавца из любой страницы товара.
    Работает на любом сайте без специфичных селекторов.
    """
    soup = BeautifulSoup(html, "html.parser")
    result = {
        "title": None,
        "price": None,
        "price_original": None,
        "currency": None,
        "in_stock": None,
        "seller": None,
        "url": url,
        "marketplace": _detect_marketplace(url),
    }

    # 1. JSON-LD (самый надёжный — стандарт разметки)
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") in ("Product", "Offer"):
                    result["title"] = result["title"] or item.get("name")
                    offers = item.get("offers") or item
                    if isinstance(offers, list):
                        offers = offers[0]
                    if isinstance(offers, dict):
                        price = offers.get("price") or offers.get("lowPrice")
                        if price:
                            try:
                                result["price"] = float(str(price).replace(",","").replace(" ",""))
                            except ValueError:
                                pass
                        result["currency"] = result["currency"] or offers.get("priceCurrency")
                        avail = offers.get("availability","")
                        if avail:
                            result["in_stock"] = "InStock" in avail
                    seller = item.get("seller") or item.get("brand")
                    if isinstance(seller, dict):
                        seller = seller.get("name")
                    result["seller"] = result["seller"] or seller
        except Exception:
            continue

    # 2. Open Graph мета-теги
    og_title = soup.find("meta", property="og:title")
    if og_title and not result["title"]:
        result["title"] = og_title.get("content")

    # 3. Заголовок страницы как последний вариант для названия
    if not result["title"]:
        h1 = soup.find("h1")
        if h1:
            result["title"] = h1.get_text(strip=True)
        elif soup.title:
            result["title"] = soup.title.get_text(strip=True)

    # 4. Универсальный поиск цены по паттернам
    if not result["price"]:
        result["price"], result["currency"] = _find_price_universal(soup, url)

    # 5. Наличие по ключевым словам
    if result["in_stock"] is None:
        result["in_stock"] = _find_stock_status(soup)

    # 6. Продавец
    if not result["seller"]:
        result["seller"] = _find_seller(soup)

    return result


def _find_price_universal(soup: BeautifulSoup, url: str) -> tuple:
    """
    Универсальный поиск цены — работает на любом сайте.
    Ищет числа рядом с символами валют.
    """
    # Определяем валюту по домену
    domain = url.lower()
    if any(d in domain for d in ["wildberries","ozon","yandex","market.ru"]):
        default_currency = "RUB"
        currency_symbols = ["₽", "руб", "rub"]
    elif any(d in domain for d in ["1688","taobao","jd.com"]):
        default_currency = "CNY"
        currency_symbols = ["¥", "￥", "元", "cny", "rmb"]
    else:
        default_currency = "USD"
        currency_symbols = ["$", "usd", "€", "eur", "£"]

    # Паттерны CSS классов с ценой (универсальные)
    price_patterns = [
        r"price",
        r"Price",
        r"cost",
        r"amount",
    ]
    price_selectors = []
    for p in price_patterns:
        price_selectors += soup.find_all(class_=re.compile(p, re.I))
        price_selectors += soup.find_all(attrs={"data-testid": re.compile(p, re.I)})
        price_selectors += soup.find_all(attrs={"itemprop": re.compile(p, re.I)})

    candidates = []
    for tag in price_selectors:
        text = tag.get_text(strip=True)
        # Ищем числа в тексте
        nums = re.findall(r"[\d\s]+[.,]?\d*", text.replace("\xa0", " "))
        for n in nums:
            clean = re.sub(r"[^\d.]", "", n.replace(",","."))
            if clean and 1 <= len(clean) <= 10:
                try:
                    val = float(clean)
                    if 0.01 < val < 10_000_000:  # разумный диапазон цен
                        candidates.append(val)
                except ValueError:
                    pass

    # Берём наиболее вероятную цену (медиана, чтобы не брать скидку в % как цену)
    if candidates:
        candidates.sort()
        # Берём значение в середине диапазона — обычно это и есть цена
        price = candidates[len(candidates)//2]
        return price, default_currency

    return None, default_currency


def _find_stock_status(soup: BeautifulSoup) -> bool:
    """Определяет наличие товара по тексту страницы"""
    text = soup.get_text().lower()
    out_of_stock_phrases = [
        "out of stock", "нет в наличии", "нет на складе",
        "sold out", "недоступно", "закончился", "unavailable",
        "не в наличии", "снят с продажи",
    ]
    in_stock_phrases = [
        "в наличии", "in stock", "available", "есть на складе",
        "добавить в корзину", "add to cart", "купить", "buy now",
        "заказать", "order now",
    ]
    for phrase in out_of_stock_phrases:
        if phrase in text:
            return False
    for phrase in in_stock_phrases:
        if phrase in text:
            return True
    return True  # по умолчанию считаем что в наличии


def _find_seller(soup: BeautifulSoup) -> Optional[str]:
    """Ищет имя продавца на странице"""
    seller_attrs = ["seller", "store", "shop", "vendor", "merchant", "brand", "supplier"]
    for attr in seller_attrs:
        tag = soup.find(attrs={"itemprop": attr})
        if tag:
            text = tag.get_text(strip=True)
            if text and len(text) < 100:
                return text
        tag = soup.find(class_=re.compile(attr, re.I))
        if tag:
            text = tag.get_text(strip=True)
            if text and 2 < len(text) < 100:
                return text
    return None


def _detect_marketplace(url: str) -> str:
    url = url.lower()
    mapping = {
        "wildberries": "wildberries",
        "wb.ru": "wildberries",
        "ozon.ru": "ozon",
        "aliexpress": "aliexpress",
        "1688.com": "1688",
        "alibaba.com": "alibaba",
        "taobao.com": "taobao",
        "ebay.com": "ebay",
        "made-in-china": "made-in-china",
        "jd.com": "jd",
        "yandex.market": "yandex_market",
        "market.yandex": "yandex_market",
    }
    for key, name in mapping.items():
        if key in url:
            return name
    return "unknown"


# ── Основные функции ───────────────────────────────────────────────────────────

async def scrape_url(
    url: str,
    extract_schema: Optional[dict] = None,
    proxy: Optional[str] = None,
    wait_for: Optional[str] = None,
    timeout: int = 30000,
) -> dict:
    """
    Главная функция скрейпинга.
    Открывает страницу в Playwright, рендерит JS, извлекает данные.
    """
    async with async_playwright() as p:
        browser, context = await _make_context(p, proxy)
        try:
            page = await context.new_page()

            # Блокируем ненужные ресурсы (ускоряет загрузку)
            await page.route("**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf}", lambda r: r.abort())

            await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            html = await _wait_and_get_content(page, wait_for, timeout)

            # Скриншот для отладки (можно убрать)
            # await page.screenshot(path="debug.png")

            markdown = _html_to_markdown(html)
            structured = _extract_structured_data(html, url)

            return {
                "markdown": markdown[:5000],  # обрезаем до разумного размера
                "structured": structured,
                "metadata": {
                    "url": url,
                    "title": structured.get("title"),
                    "status": 200,
                }
            }
        finally:
            await browser.close()


async def search_and_scrape(
    query: str,
    sites: list[str],
    max_results: int = 5,
    proxy: Optional[str] = None,
    extract_schema: Optional[dict] = None,
) -> list[dict]:
    """
    Ищет товар через Google/Yandex с site: фильтром,
    затем скрейпит найденные страницы через Playwright.
    Это самый надёжный способ найти редкие артикулы.
    """
    async with async_playwright() as p:
        browser, context = await _make_context(p, proxy)
        try:
            all_results = []

            if sites:
                # Ищем по каждому сайту отдельно
                for site in sites:
                    urls = await _google_search(context, query, site, max_results)
                    for url in urls[:max_results]:
                        try:
                            result = await _scrape_with_context(context, url, extract_schema)
                            all_results.append(result)
                        except Exception as e:
                            all_results.append({
                                "url": url,
                                "error": str(e),
                                "structured": {"marketplace": _detect_marketplace(url)},
                            })
            else:
                # Свободный поиск по всем площадкам
                urls = await _google_search(context, query, None, max_results * 3)
                for url in urls[:max_results]:
                    try:
                        result = await _scrape_with_context(context, url, extract_schema)
                        all_results.append(result)
                    except Exception as e:
                        all_results.append({"url": url, "error": str(e)})

            return all_results
        finally:
            await browser.close()


async def _google_search(context: BrowserContext, query: str,
                          site: Optional[str], max_results: int) -> list[str]:
    """Ищет через Google с site: фильтром, возвращает список URL"""
    search_query = f"{query} site:{site}" if site else query
    search_url = f"https://www.google.com/search?q={quote_plus(search_query)}&num={max_results}"

    page = await context.new_page()
    try:
        await page.goto(search_url, timeout=20000, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(1.5, 3.0))  # имитируем человека

        # Извлекаем ссылки из результатов Google
        links = await page.evaluate("""
            () => {
                const results = [];
                // Обычные результаты поиска
                document.querySelectorAll('a[href]').forEach(a => {
                    const href = a.href;
                    // Фильтруем только реальные ссылки (не google.com сервисы)
                    if (href && href.startsWith('http') &&
                        !href.includes('google.') &&
                        !href.includes('youtube.') &&
                        !href.includes('accounts.') &&
                        !href.includes('maps.') &&
                        href.length > 20) {
                        results.push(href);
                    }
                });
                return [...new Set(results)];  // убираем дубли
            }
        """)

        # Если site указан — фильтруем строго по домену
        if site:
            links = [l for l in links if site.replace("www.","") in l]

        return links[:max_results]
    except Exception:
        return []
    finally:
        await page.close()


async def _scrape_with_context(context: BrowserContext, url: str,
                                extract_schema: Optional[dict]) -> dict:
    """Скрейпит страницу используя существующий браузерный контекст"""
    page = await context.new_page()
    try:
        await page.route("**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2}", lambda r: r.abort())
        await page.goto(url, timeout=25000, wait_until="domcontentloaded")

        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass

        # Небольшой скролл
        await page.evaluate("window.scrollBy(0, 500)")
        await asyncio.sleep(0.5)

        html = await page.content()
        structured = _extract_structured_data(html, url)
        markdown = _html_to_markdown(html)

        return {
            "url": url,
            "structured": structured,
            "markdown": markdown[:3000],
        }
    finally:
        await page.close()
