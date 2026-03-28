"""
Умный экстрактор данных на базе Claude.
Принимает сырой HTML и список нужных полей — возвращает структурированный JSON.
Не требует CSS-селекторов. Работает с любым сайтом.
"""
import re
import json
import logging
from typing import Any, Optional
from bs4 import BeautifulSoup
import anthropic

from config import settings

logger = logging.getLogger(__name__)


def _clean_html(html: str, max_chars: int = 80_000) -> str:
    """Убираем мусор из HTML, оставляем текст и важные атрибуты."""
    soup = BeautifulSoup(html, "lxml")

    # Удаляем скрипты, стили, SVG — они не нужны для извлечения данных
    for tag in soup(["script", "style", "svg", "noscript", "head", "footer", "nav"]):
        tag.decompose()

    # Оставляем только значимые атрибуты
    for tag in soup.find_all(True):
        allowed = {"href", "src", "data-price", "data-product", "itemprop", "content", "class", "id"}
        attrs_to_remove = [k for k in list(tag.attrs.keys()) if k not in allowed]
        for attr in attrs_to_remove:
            del tag[attr]

    text = soup.get_text(separator="\n", strip=True)
    # Убираем повторяющиеся пустые строки
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Обрезаем если слишком длинно (лимит токенов Claude)
    if len(text) > max_chars:
        # Оставляем начало (заголовки, цены обычно вверху) и середину
        text = text[:max_chars // 2] + "\n...[обрезано]...\n" + text[-(max_chars // 4):]

    return text


def _extract_links(html: str, base_url: str = "") -> list[str]:
    """Извлекаем все ссылки на товары из HTML."""
    soup = BeautifulSoup(html, "lxml")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http"):
            links.append(href)
        elif href.startswith("/") and base_url:
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            links.append(f"{parsed.scheme}://{parsed.netloc}{href}")
    return list(dict.fromkeys(links))  # deduplicate, preserve order


class ClaudeExtractor:
    """Извлекает данные из HTML с помощью Claude."""

    def __init__(self):
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY не задан в .env")
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def extract(
        self,
        html: str,
        url: str,
        product_name: str,
        fields: list[str],
    ) -> dict[str, Any]:
        """
        Извлекает указанные поля из HTML страницы.

        Args:
            html: сырой HTML страницы
            url: URL страницы (для контекста)
            product_name: название товара (для контекста поиска)
            fields: список полей для извлечения (price, currency, seller, product_url и т.д.)

        Returns:
            dict с извлечёнными полями + мета-данные
        """
        cleaned = _clean_html(html)
        links = _extract_links(html, url)

        fields_description = "\n".join(f"- {f}" for f in fields)
        links_sample = "\n".join(links[:30]) if links else "нет ссылок"

        prompt = f"""Ты — эксперт по парсингу веб-страниц.
Тебе нужно извлечь данные о товаре со страницы сайта.

URL страницы: {url}
Товар для поиска: {product_name}

Нужно извлечь следующие поля:
{fields_description}

Ссылки на странице (первые 30):
{links_sample}

Текст страницы:
{cleaned}

Верни JSON объект с извлечёнными данными. Правила:
1. Для каждого поля верни найденное значение или null если не нашёл
2. Для поля "price" верни только число (без валюты), например: 1299.99
3. Для поля "currency" верни код валюты: RUB, USD, EUR, KZT и т.д.
4. Для поля "product_url" верни прямую ссылку на карточку товара
5. Для поля "seller" или "seller_contact" верни название магазина/продавца и/или контакт
6. Для поля "availability" верни: "in_stock", "out_of_stock" или "unknown"
7. Если на странице несколько товаров — верни массив в поле "items", каждый элемент содержит запрошенные поля
8. Добавь поле "page_type": "product_card" | "catalog" | "search_results" | "other"
9. Добавь поле "confidence": от 0 до 1 (насколько уверен в данных)

Верни ТОЛЬКО валидный JSON, без пояснений.
"""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            response_text = message.content[0].text.strip()

            # Извлекаем JSON из ответа (на случай если Claude добавил пояснения)
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if json_match:
                return json.loads(json_match.group())
            return {"error": "Claude не вернул JSON", "raw": response_text}

        except json.JSONDecodeError as e:
            return {"error": f"Ошибка парсинга JSON: {e}"}
        except Exception as e:
            logger.error(f"Ошибка Claude API: {e}")
            return {"error": str(e)}


# Singleton
_extractor: Optional[ClaudeExtractor] = None


def get_extractor() -> ClaudeExtractor:
    global _extractor
    if _extractor is None:
        _extractor = ClaudeExtractor()
    return _extractor
