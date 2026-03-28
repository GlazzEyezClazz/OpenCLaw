"""
Universal Parser API
Совместим с n8n / Neuro42 / OpenClaw через REST JSON API.

Endpoints:
  POST /scrape          — синхронный парсинг (ждёт результат)
  POST /scrape/async    — асинхронный (возвращает job_id сразу)
  GET  /jobs/{job_id}   — статус и результат асинхронного задания
  GET  /health          — проверка работоспособности
  GET  /docs            — автодокументация (Swagger UI)
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import settings
from scraper.engine import ScraperEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Universal Parser API",
    description="Универсальный парсер данных с обходом антибот-систем. "
                "Совместим с n8n, Neuro42, OpenClaw.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Хранилище задач (в продакшне заменить на Redis)
jobs: Dict[str, Dict[str, Any]] = {}


# ─────────────────────────── Pydantic модели ───────────────────────────────

class ScrapeOptions(BaseModel):
    js_render: str = Field(
        default="auto",
        description="Режим JS: 'never' (только httpx), 'always' (playwright), 'auto' (авто-выбор)",
    )
    proxies: Optional[List[str]] = Field(
        default=None,
        description="Список прокси: ['http://user:pass@host:port', ...]",
        example=["http://user:pass@1.2.3.4:8080"],
    )
    timeout: int = Field(default=30, description="Таймаут запроса в секундах")
    max_retries: int = Field(default=3, description="Кол-во повторных попыток")


class ScrapeTask(BaseModel):
    product: str = Field(description="Название товара для поиска", example="iPhone 15 Pro 256GB")
    sites: List[str] = Field(
        description="Список сайтов для парсинга",
        example=["wildberries.ru", "ozon.ru", "avito.ru"],
    )
    extract: List[str] = Field(
        default=["price", "currency", "product_url", "seller", "availability"],
        description="Поля для извлечения",
        example=["price", "currency", "product_url", "seller", "availability", "rating", "reviews_count"],
    )
    search_query: Optional[str] = Field(
        default=None,
        description="Кастомный поисковый запрос (если отличается от product)",
    )


class ScrapeRequest(BaseModel):
    tasks: List[ScrapeTask] = Field(description="Список задач парсинга")
    options: Optional[ScrapeOptions] = Field(default=None, description="Настройки парсера")
    callback_url: Optional[str] = Field(
        default=None,
        description="URL для webhook-колбэка (для /scrape/async)",
        example="https://your-n8n.com/webhook/parser-result",
    )


class JobStatus(BaseModel):
    job_id: str
    status: str  # pending | running | done | error
    created_at: str
    finished_at: Optional[str] = None
    results: Optional[List[Any]] = None
    error: Optional[str] = None


# ─────────────────────────── Handlers ──────────────────────────────────────

@app.post(
    "/scrape",
    summary="Синхронный парсинг",
    description="Ждёт завершения и возвращает результаты. Подходит для небольших задач.",
    response_description="Список результатов по каждому сайту",
)
async def scrape_sync(request: ScrapeRequest):
    """
    Пример для n8n/Neuro42:
    - HTTP Request node → POST /scrape
    - Body: { "tasks": [...], "options": {...} }
    - Ответ приходит когда парсинг завершён
    """
    engine = ScraperEngine(request.options.model_dump() if request.options else {})
    tasks_data = [t.model_dump() for t in request.tasks]

    results = await engine.run(tasks_data)
    return {
        "status": "done",
        "total": len(results),
        "results": results,
    }


@app.post(
    "/scrape/async",
    summary="Асинхронный парсинг с webhook",
    description="Сразу возвращает job_id. Результат отправляется на callback_url или доступен через GET /jobs/{job_id}",
)
async def scrape_async(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """
    Для долгих задач. Схема для n8n:
    1. POST /scrape/async → получаем job_id
    2. Wait node → GET /jobs/{job_id} до status=done
    ИЛИ указать callback_url — придёт POST с результатами
    """
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "finished_at": None,
        "results": None,
        "error": None,
    }
    background_tasks.add_task(_run_job, job_id, request)
    return {"job_id": job_id, "status": "pending", "poll_url": f"/jobs/{job_id}"}


@app.get(
    "/jobs/{job_id}",
    summary="Статус асинхронного задания",
    response_model=JobStatus,
)
async def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@app.get("/jobs", summary="Список всех заданий")
async def list_jobs():
    return {"total": len(jobs), "jobs": list(jobs.values())}


@app.delete("/jobs/{job_id}", summary="Удалить задание из истории")
async def delete_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    del jobs[job_id]
    return {"deleted": job_id}


@app.post(
    "/fetch",
    summary="Просто загрузить URL",
    description="Загружает произвольный URL и возвращает HTML. Полезно для тестирования стратегий.",
)
async def fetch_url(
    url: str,
    js_render: str = "auto",
    proxy: Optional[str] = None,
):
    engine = ScraperEngine({"js_render": js_render, "proxies": [proxy] if proxy else []})
    result = await engine.fetch_with_fallback(url, js_render)
    return {
        "url": result.url,
        "status_code": result.status_code,
        "strategy_used": result.strategy_used,
        "html_length": len(result.html),
        "html_preview": result.html[:2000],
        "error": result.error,
    }


@app.get("/health", summary="Проверка работоспособности")
async def health():
    return {
        "status": "ok",
        "anthropic_configured": bool(settings.anthropic_api_key),
        "proxies_configured": len(settings.proxies),
        "max_concurrent": settings.max_concurrent_tasks,
    }


# ─────────────────────────── Background task ───────────────────────────────

async def _run_job(job_id: str, request: ScrapeRequest):
    jobs[job_id]["status"] = "running"
    try:
        engine = ScraperEngine(request.options.model_dump() if request.options else {})
        tasks_data = [t.model_dump() for t in request.tasks]
        results = await engine.run(tasks_data)

        jobs[job_id].update({
            "status": "done",
            "results": results,
            "finished_at": datetime.now().isoformat(),
        })

        # Отправляем webhook если указан callback_url
        if request.callback_url:
            await _send_callback(request.callback_url, jobs[job_id])

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        jobs[job_id].update({
            "status": "error",
            "error": str(e),
            "finished_at": datetime.now().isoformat(),
        })


async def _send_callback(url: str, data: dict):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            await client.post(url, json=data)
            logger.info(f"Webhook отправлен на {url}")
    except Exception as e:
        logger.error(f"Ошибка отправки webhook на {url}: {e}")


# ─────────────────────────── Entry point ───────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )
