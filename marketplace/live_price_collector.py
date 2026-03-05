#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
from pathlib import Path
from datetime import datetime, UTC
from openpyxl import Workbook

from DrissionPage import ChromiumPage, ChromiumOptions

WORKDIR = Path('/home/safeuser/.openclaw/workspace')
OUT_XLSX = WORKDIR / 'macbook_16_m1pro_32_512_live.xlsx'
SECRETS = Path('/home/safeuser/.clawdbot/secrets')

TARGETS = [
    {
        'marketplace': 'Wildberries',
        'url': 'https://www.wildberries.ru/catalog/359063793/detail.aspx',
        'currency': 'RUB',
    },
    {
        'marketplace': 'Ozon',
        'url': 'https://www.ozon.ru/product/apple-macbook-pro-noutbuk-16-apple-m1-pro-10c-cpu-16c-gpu-ram-32-gb-ssd-512-gb-apple-m1-pro-macos-1878151954/',
        'currency': 'RUB',
    },
    {
        'marketplace': 'AliExpress',
        'url': 'https://www.aliexpress.com/item/1005007954604674.html',
        'currency': 'USD',
    },
]

PRICE_PATTERNS = [
    re.compile(r'"price"\s*:\s*"?(\d{2,9}(?:[\.,]\d{1,2})?)"?', re.I),
    re.compile(r'"priceU"\s*:\s*"?(\d{2,9}(?:[\.,]\d{1,2})?)"?', re.I),
    re.compile(r'"finalPrice"\s*:\s*"?(\d{2,9}(?:[\.,]\d{1,2})?)"?', re.I),
    re.compile(r'"priceWithDiscount"\s*:\s*"?(\d{2,9}(?:[\.,]\d{1,2})?)"?', re.I),
    re.compile(r'(\d{2,9}[\.,]\d{2})\s*(?:₽|RUB|\$|USD)', re.I),
]

TITLE_PATTERNS = [
    re.compile(r'<title>(.*?)</title>', re.I | re.S),
    re.compile(r'"name"\s*:\s*"([^"]{10,200})"', re.I),
]


def load_proxy():
    p = SECRETS / 'proxies.json'
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        return data.get('rotating')
    except Exception:
        return None


def norm_price(raw: str):
    x = raw.replace(' ', '').replace('\xa0', '').replace(',', '.')
    try:
        return float(x)
    except Exception:
        return None


def extract_price(html: str):
    vals = []
    for pat in PRICE_PATTERNS:
        for m in pat.finditer(html):
            v = norm_price(m.group(1))
            if v and 100 < v < 10000000:
                vals.append(v)
    if not vals:
        return None
    return min(vals)


def extract_title(html: str):
    for pat in TITLE_PATTERNS:
        m = pat.search(html)
        if m:
            t = re.sub(r'\s+', ' ', m.group(1)).strip()
            if t:
                return t[:200]
    return 'Не удалось извлечь название'


def setup_browser():
    co = ChromiumOptions()
    co.headless(True)
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    co.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36')
    proxy = load_proxy()
    if proxy:
        co.set_proxy(proxy)
    return ChromiumPage(co)


def collect():
    page = setup_browser()
    rows = []
    for t in TARGETS:
        market = t['marketplace']
        url = t['url']
        currency = t['currency']
        try:
            page.get(url, timeout=30)
            page.wait.doc_loaded(timeout=20)
            html = page.html or ''
            title = extract_title(html)
            price = extract_price(html)
            note = 'ok' if price else 'Цена не найдена (возможно anti-bot)'
            rows.append([market, title, price, currency, url, note])
        except Exception as e:
            rows.append([market, 'Ошибка открытия карточки', None, currency, url, f'Ошибка: {str(e)[:120]}'])
    try:
        page.quit()
    except Exception:
        pass
    return rows


def write_xlsx(rows):
    wb = Workbook()
    ws = wb.active
    ws.title = 'цены'
    ws.append(['Маркетплейс', 'Название товара', 'Цена', 'Валюта', 'Ссылка', 'Статус'])
    for r in rows:
        ws.append(r)
    ws.append([])
    ws.append(['Обновлено (UTC)', datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')])
    wb.save(OUT_XLSX)


def main():
    rows = collect()
    write_xlsx(rows)
    print(str(OUT_XLSX))


if __name__ == '__main__':
    main()
