# Anti-bot plan for WB / Ozon / DNS (production)

## Что уже сделано автоматически

1. Подготовлена инфраструктура секретов:
   - `/home/safeuser/.clawdbot/secrets/captcha.json`
   - `/home/safeuser/.clawdbot/secrets/proxies.json`
2. Добавлен preflight-чек:
   - `/home/safeuser/.openclaw/workspace/marketplace/preflight.py`
3. Установлены stealth-компоненты:
   - `rebrowser-playwright`
   - `playwright-bot-bypass` skill
4. Подтверждено, что без прокси + captcha key full bypass пока невозможен.

## Выбранное решение для капчи (лучшее по стабильности/скорости)

**CapSolver** (основной)

Почему:
- быстрее на слайдер/anti-bot сценариях,
- хорошее покрытие современных challenge-паттернов,
- проще в эксплуатации для потокового парсинга.

Резерв: **2captcha**.

## Критические условия для регулярного сбора цен

1. Резидентские прокси (RU) + ротация IP
2. CapSolver API key
3. Стабильные сессии (cookie/profile reuse)
4. Ограничение частоты запросов (throttle + jitter)
5. Жесткий фильтр релевантности (16 + M1 Pro + 32 + 512)

## Команда проверки готовности

```bash
python3 /home/safeuser/.openclaw/workspace/marketplace/preflight.py
```

`ready_for_full_bypass: True` = можно запускать прод-контур извлечения цен.
