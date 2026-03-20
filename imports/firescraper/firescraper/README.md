# 🔥 FireScraper — Self-hosted аналог Firecrawl

Использует **Playwright + Chromium** (реальный браузер) для обхода JS-защиты.
Именно это делает Firecrawl платным — теперь у тебя есть то же самое бесплатно.

---

## ⚡ Почему это работает там где наши парсеры не работали

| Старый парсер | FireScraper |
|---|---|
| httpx — простой HTTP запрос | Playwright — настоящий браузер |
| JS не выполняется | JS выполняется полностью |
| Цены в JS переменных = пусто | Цены рендерятся как в браузере |
| Блокируется anti-bot | navigator.webdriver скрыт |
| Нужны специфичные селекторы для каждого сайта | Универсальное извлечение по любому сайту |

---

## 🚀 Установка на VPS (отправь это OpenClaw)

```bash
# 1. Установи зависимости
cd /opt/firescraper
pip3 install -r requirements.txt

# 2. Установи браузер Chromium (одна команда)
playwright install chromium
playwright install-deps chromium

# 3. Запусти через systemd
cat > /etc/systemd/system/firescraper.service << 'EOF'
[Unit]
Description=FireScraper API
After=network.target

[Service]
WorkingDirectory=/opt/firescraper
ExecStart=/usr/bin/python3 main.py
Restart=always
User=root
Environment=DISPLAY=:99

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable firescraper
systemctl start firescraper

# 4. Проверь
curl http://localhost:8000/health
```

---

## 📡 API — использование в n8n

### Скрейпинг по прямой ссылке
```
POST http://ВАШ_VPS_IP:8000/v1/scrape
Content-Type: application/json

{
  "url": "https://www.alibaba.com/product-detail/HIKROBOT-MV-CH050-10CC-2-3-1600647366781.html"
}
```

**Ответ:**
```json
{
  "success": true,
  "data": {
    "structured": {
      "title": "HIKROBOT MV-CH050-10CC 12MP CameraLink Camera",
      "price": 450.00,
      "currency": "USD",
      "in_stock": true,
      "seller": "Shenzhen Vision Store",
      "url": "https://...",
      "marketplace": "alibaba"
    },
    "markdown": "# HIKROBOT MV-CH050-10CC\n\n**Price:** $450..."
  }
}
```

### Поиск по названию (самый мощный режим)
```
POST http://ВАШ_VPS_IP:8000/v1/search
Content-Type: application/json

{
  "query": "MV-CH050-10CC",
  "sites": ["aliexpress.com", "alibaba.com", "1688.com", "ebay.com", "wildberries.ru"],
  "max_results": 3
}
```

**Ответ:**
```json
{
  "success": true,
  "query": "MV-CH050-10CC",
  "total": 12,
  "data": [
    {
      "url": "https://www.aliexpress.com/item/...",
      "structured": {
        "marketplace": "aliexpress",
        "title": "MV-CH050-10CC Industrial Camera",
        "price": 380.00,
        "currency": "USD",
        "in_stock": true,
        "seller": "Industrial Vision Store"
      }
    }
  ]
}
```

### Свободный поиск (без указания сайтов — ищет везде)
```json
{
  "query": "MV-CH050-10CC купить",
  "max_results": 10
}
```

---

## 🔧 n8n Workflow — ноды

### Нода 1: HTTP Request → /v1/search
```
Method: POST
URL: http://ВАШ_IP:8000/v1/search
Body:
{
  "query": "{{ $json.product_name }}",
  "sites": ["aliexpress.com", "alibaba.com", "1688.com", "ebay.com"],
  "max_results": 5
}
```

### Нода 2: Code — обработка результатов
```javascript
const data = $input.first().json;
const results = data.data || [];

return results
  .filter(r => r.structured?.price)
  .sort((a, b) => (a.structured.price || 99999) - (b.structured.price || 99999))
  .map(r => ({
    json: {
      marketplace: r.structured.marketplace,
      title: r.structured.title,
      price: r.structured.price,
      currency: r.structured.currency,
      in_stock: r.structured.in_stock,
      seller: r.structured.seller,
      url: r.url,
    }
  }));
```

---

## 🔒 Прокси для Китая

Для 1688/Taobao добавь в запрос:
```json
{
  "query": "MV-CH050-10CC",
  "sites": ["1688.com"],
  "proxy": "http://user:password@proxy-cn-host:8080"
}
```

Сервисы прокси с CN IP:
- [IPRoyal](https://iproyal.com) — резидентные ~$7/GB
- [Bright Data](https://brightdata.com) — дороже, надёжнее

---

## 🐳 Docker (альтернативный запуск)

```bash
docker build -t firescraper .
docker run -d -p 8000:8000 --name firescraper firescraper
```
