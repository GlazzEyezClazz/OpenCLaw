# Интеграция с Neuro42 / n8n / OpenClaw

## Архитектура парсера

```
Запрос (JSON)
     ↓
  FastAPI REST API  (порт 8000)
     ↓
  ScraperEngine
     ↓ (авто-выбор стратегии)
  ┌─────────────────────────────────┐
  │  Стратегия 1: httpx             │  ← быстро, для простых сайтов
  │  Стратегия 2: cloudscraper      │  ← Cloudflare bypass
  │  Стратегия 3: playwright stealth│  ← DataDome, Akamai, PerimeterX
  └─────────────────────────────────┘
     ↓
  Claude (умное извлечение данных из HTML)
     ↓
  JSON результат
```

---

## Neuro42 / n8n — Синхронная интеграция

**Нода: HTTP Request**
- Method: `POST`
- URL: `http://localhost:8000/scrape`
- Body (JSON):
```json
{
  "tasks": [
    {
      "product": "{{ $json.product_name }}",
      "sites": ["wildberries.ru", "ozon.ru", "avito.ru"],
      "extract": ["price", "currency", "product_url", "seller", "availability"]
    }
  ],
  "options": { "js_render": "auto", "timeout": 30 }
}
```

**Ответ:**
```json
{
  "status": "done",
  "total": 3,
  "results": [
    {
      "site": "wildberries.ru",
      "product": "iPhone 15 Pro",
      "status": "ok",
      "price": 89990,
      "currency": "RUB",
      "product_url": "https://...",
      "seller": "WB Seller",
      "availability": "in_stock",
      "strategy_used": "httpx"
    }
  ]
}
```

---

## Neuro42 / n8n — Асинхронная интеграция (webhook)

### Шаг 1: Запуск задания
**Нода: HTTP Request**
- POST `http://localhost:8000/scrape/async`
- Добавить в body: `"callback_url": "https://your-n8n.com/webhook/XXX"`

### Шаг 2: Webhook Trigger нода
- Принимает POST запрос с готовыми результатами

**ИЛИ**

### Шаг 2 (polling): Loop Until
- GET `http://localhost:8000/jobs/{{ $json.job_id }}`
- Условие: `{{ $json.status }} === "done"`
- Пауза: 5 секунд

---

## OpenClaw интеграция

OpenClaw поддерживает HTTP-ноды с JSON. Схема та же:
1. Создать HTTP Action node → POST /scrape
2. Map входные переменные в поля `tasks`
3. Из ответа взять `results[0].price`, `results[0].product_url` и т.д.

---

## Поддерживаемые поля extract

| Поле | Описание | Пример значения |
|------|----------|-----------------|
| `price` | Цена (число) | `89990` |
| `currency` | Код валюты | `RUB`, `USD`, `EUR` |
| `product_url` | Ссылка на карточку | `https://...` |
| `seller` | Название продавца | `"ООО Техносфера"` |
| `seller_contact` | Контакт продавца | `"+7 800 000-00-00"` |
| `availability` | Наличие | `in_stock` / `out_of_stock` |
| `rating` | Рейтинг | `4.8` |
| `reviews_count` | Кол-во отзывов | `1234` |
| `location` | Местоположение | `"Москва"` |
| `description` | Описание товара | `"..."` |
| `images` | Ссылки на фото | `["https://..."]` |
| `brand` | Бренд | `"Apple"` |
| `sku` | Артикул | `"MQ9R3LL/A"` |

Можно добавить любое кастомное поле — Claude его найдёт по смыслу.

---

## Запуск

```bash
# 1. Установка
setup.bat          # Windows
# или
pip install -r requirements.txt && playwright install chromium

# 2. Настройка
cp .env.example .env
# Вписать ANTHROPIC_API_KEY=sk-ant-...

# 3. Запуск
python server.py

# Docker
docker-compose up -d
```

API будет доступен на `http://localhost:8000`
Swagger документация: `http://localhost:8000/docs`
