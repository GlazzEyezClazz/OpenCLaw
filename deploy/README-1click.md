# VPS-only Bootstrap (OpenClaw)

Цель: один запуск разворачивает окружение на новом VPS/ноуте и подтягивает рабочее состояние.

## Что делает

- ставит Docker (если нет)
- ставит Node.js (если нет)
- ставит OpenClaw (если нет)
- создает `.env` шаблон
- синхронизирует `skills/`, `memory/`, `configs/`, `patches/`
- прогоняет healthcheck
- перезапускает gateway

## Быстрый запуск (на новом VPS/ноуте)

```bash
cd deploy
bash install.sh
bash up.sh
```

Если переносишь в другой хост архивом:

```bash
tar -xzf deploy_vps_bootstrap_v2.tar.gz
cd deploy
bash install.sh && bash up.sh
```

## Структура

- `install.sh` — базовая установка + проверки
- `up.sh` — восстановление состояния + рестарт gateway
- `restore-state.sh` — синхронизация skills/memory/configs
- `scripts/healthcheck.sh` — самодиагностика
- `configs/` — сюда кладем рабочие конфиги
- `patches/` — патчи/хотфиксы

## Важно

- Этот пакет может включать `configs/openclaw.env` и `configs/openclaw.json` (секреты/токены). Храни и передавай архив как приватный.
- Восстановление идемпотентное: повторный запуск `install.sh` и `up.sh` безопасен.
- Логи установки: `deploy/logs/`.
