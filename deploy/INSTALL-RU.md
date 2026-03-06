# Установка v2 (пошагово)

## Что это ставит

Пакет поднимает перенос сборки OpenClaw с этого VPS:
- системные зависимости (Docker, Node.js, OpenClaw CLI)
- конфиг `~/.openclaw/openclaw.json`
- env `~/.openclaw/.env`
- workspace state: `skills/`, `memory/`, `scripts/`, `package*.json`

## Быстрый запуск на новом хосте

```bash
# 1) распаковать
mkdir -p ~/openclaw-migrate && cd ~/openclaw-migrate
tar -xzf deploy_vps_bootstrap_v2.tar.gz

# 2) запустить
cd deploy
bash bootstrap.sh

# 3) проверить
openclaw gateway status
```

## Если нужен запуск по шагам

```bash
cd deploy
bash install.sh
bash up.sh
```

## Что важно знать

1. Сборка **максимально близкая к текущей**, потому что переносится наш `openclaw.json` и `.env`.
2. Но 100% бит-в-бит идентичность может отличаться из-за:
   - версии ОС на новом хосте,
   - текущих версий пакетов apt/npm,
   - внешних сервисов (сети, DNS, доступность репозиториев).
3. Если нужен полностью детерминированный вариант, следующий шаг — зафиксировать версии (pin) и добавить preflight-проверку ОС.

## Частые команды

```bash
# перезапуск gateway
openclaw gateway restart

# статус gateway
openclaw gateway status

# логи установки
ls -lah deploy/logs
```
