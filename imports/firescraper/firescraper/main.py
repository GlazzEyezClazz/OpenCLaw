"""
FireScraper — self-hosted аналог Firecrawl
Использует Playwright для рендеринга JS, обхода anti-bot защиты.
Именно так работает Firecrawl под капотом.

Запуск:
  pip install -r requirements.txt
  playwright install chromium
  python main.py
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

from scraper import scrape_url, search_and_scrape

app = FastAPI(title="FireScraper", description="Self-hosted Firecrawl alternative", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Модели запросов ────────────────────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    url: str
    extract: Optional[dict] = None      # {"price": "...", "title": "..."} — что достать
    proxy: Optional[str] = None
    wait_for: Optional[str] = None      # CSS селектор — ждать появления элемента
    timeout: int = 30000                # мс

class SearchRequest(BaseModel):
    query: str                          # "MV-CH050-10CC site:aliexpress.com"
    sites: list[str] = []              # ["aliexpress.com", "1688.com", ...]
    max_results: int = 5
    proxy: Optional[str] = None
    extract_schema: Optional[dict] = None  # что парсить с найденных страниц


# ── Эндпоинты ─────────────────────────────────────────────────────────────────

@app.post("/v1/scrape")
async def scrape(req: ScrapeRequest):
    """
    Скрейпит URL через Playwright (рендерит JS, обходит anti-bot).
    Возвращает markdown + структурированные данные если указан extract.

    Пример для n8n:
    POST /v1/scrape
    {"url": "https://www.alibaba.com/product-detail/...", "extract": {"price": true, "title": true}}
    """
    try:
        result = await scrape_url(
            url=req.url,
            extract_schema=req.extract,
            proxy=req.proxy,
            wait_for=req.wait_for,
            timeout=req.timeout,
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/search")
async def search(req: SearchRequest):
    """
    Ищет товар по названию через Google/Yandex, затем скрейпит найденные страницы.
    Самый мощный режим — как /agent в Firecrawl.

    Пример:
    POST /v1/search
    {
      "query": "MV-CH050-10CC",
      "sites": ["aliexpress.com", "1688.com", "alibaba.com", "ebay.com", "wildberries.ru"],
      "max_results": 5,
      "extract_schema": {"price": true, "title": true, "in_stock": true, "seller": true}
    }
    """
    try:
        results = await search_and_scrape(
            query=req.query,
            sites=req.sites,
            max_results=req.max_results,
            proxy=req.proxy,
            extract_schema=req.extract_schema,
        )
        return {"success": True, "query": req.query, "total": len(results), "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok", "engine": "playwright+chromium"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
