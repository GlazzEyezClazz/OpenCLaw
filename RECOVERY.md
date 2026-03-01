# OpenClaw Recovery Playbook (A→Я)

Репозиторий: `git@github.com:GlazzEyezClazz/OpenCLaw.git`  
Веб: https://github.com/GlazzEyezClazz/OpenCLaw

Этот документ разбит на 2 отдельные задачи:

1. **Откат к бэкапам** (когда VPS жив, но нужно вернуться к прошлому состоянию)  
2. **Полное восстановление с нуля** (когда VPS потерян/переустановлен)

---

## 0) Что считается «эталонной» конфигурацией

Ниже структура, которую мы восстанавливаем:

- Workspace: `/home/safeuser/.openclaw/workspace`
- Основной репозиторий Git: в этой же папке
- Skills:
  - `/home/safeuser/.openclaw/workspace/skills/find-skills`
  - `/home/safeuser/.openclaw/workspace/skills/google-workspace-mcp`
- Скрипты:
  - `/home/safeuser/.openclaw/workspace/scripts/daily_kb_backup.sh`
  - `/home/safeuser/.openclaw/workspace/scripts/restore_openclaw.sh`
- MCP config:
  - `/home/safeuser/.mcporter/mcporter.json`
- Google Workspace credentials (локально):
  - `/home/safeuser/.config/google-workspace-mcp/`

Бэкап по расписанию:
- Каждый день в **00:00 Asia/Yekaterinburg** = `19:00 UTC`
- Cron строка:
  - `0 19 * * * /home/safeuser/.openclaw/workspace/scripts/daily_kb_backup.sh`

---

## ЭТАП 1. ОТКАТ К БЭКАПАМ (если сервер работает)

### 1.1 Проверить, что ты в нужном репозитории

```bash
cd /home/safeuser/.openclaw/workspace
git remote -v
git branch --show-current
```

Ожидаемо:
- `origin` указывает на `git@github.com:GlazzEyezClazz/OpenCLaw.git`
- активная ветка: `master`

### 1.2 Подтянуть актуальную историю и теги

```bash
git fetch --all --tags
```

### 1.3 Посмотреть точки восстановления

**По тегам (дневные срезы):**
```bash
git tag -l "backup-*" --sort=-creatordate | head -n 30
```

**По коммитам:**
```bash
git log --oneline --decorate -n 50
```

### 1.4 Безопасный откат (рекомендуется через отдельную ветку)

1) Выбери тег, например: `backup-2026-03-01`  
2) Создай ветку восстановления от него:

```bash
git switch -c restore-2026-03-01 backup-2026-03-01
```

Теперь ты в рабочей ветке на старом состоянии.

### 1.5 Если нужно сделать это «боевым» master

⚠️ Делай только если понимаешь, что перезаписываешь текущий master.

```bash
git switch master
git reset --hard backup-2026-03-01
git push --force-with-lease origin master
```

### 1.6 Проверка после отката

```bash
pwd
ls -la
git status
crontab -l
clawhub list
mcporter config list
```

---

## ЭТАП 2. ПОЛНОЕ ВОССТАНОВЛЕНИЕ С НУЛЯ (новый VPS)

Ниже «буквально от А до Я».

## 2.1 Подготовка нового VPS

Рекомендуемая ОС: Ubuntu 24.04+.

Создай пользователя (если нужно):

```bash
adduser safeuser
usermod -aG sudo safeuser
```

Проверь:

```bash
id safeuser
```

Ожидаемо: в группах есть `sudo`.

## 2.2 Вход под safeuser

```bash
su - safeuser
```

Проверь домашнюю директорию:

```bash
pwd
# должно быть: /home/safeuser
```

## 2.3 Системные зависимости

```bash
sudo apt-get update
sudo apt-get install -y git curl build-essential libsecret-1-0 libsecret-1-dev
```

## 2.4 Установка Node.js (если не установлен)

Проверь:

```bash
node -v
npm -v
```

Если Node нет, ставь (пример через NodeSource 24.x):

```bash
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt-get install -y nodejs
```

Повторная проверка:

```bash
node -v
npm -v
```

## 2.5 Настройка SSH-доступа к GitHub

### 2.5.1 Если ключа нет — создать

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519 -C "safeuser@openclaw"
cat ~/.ssh/id_ed25519.pub
```

### 2.5.2 Добавить ключ в GitHub

Варианты:
- Account → Settings → SSH keys
- или Repo → Settings → Deploy keys (с правом write)

### 2.5.3 Добавить known_hosts и проверить

```bash
ssh-keyscan -H github.com >> ~/.ssh/known_hosts
chmod 600 ~/.ssh/known_hosts
ssh -T git@github.com
```

## 2.6 Клонирование проекта

```bash
mkdir -p /home/safeuser/.openclaw
git clone git@github.com:GlazzEyezClazz/OpenCLaw.git /home/safeuser/.openclaw/workspace
cd /home/safeuser/.openclaw/workspace
```

Проверка:

```bash
git remote -v
ls -la
```

## 2.7 Установка глобальных CLI

```bash
npm install -g openclaw clawhub mcporter
```

Проверка:

```bash
openclaw --version || true
clawhub --help | head -n 2
mcporter --help | head -n 2
```

## 2.8 Логин в ClawHub

```bash
clawhub login
clawhub whoami
```

## 2.9 Восстановление skills

```bash
cd /home/safeuser/.openclaw/workspace
clawhub install find-skills
clawhub install google-workspace-mcp --force
clawhub list
```

Ожидаемо в списке:
- `find-skills`
- `google-workspace-mcp`

## 2.10 Настройка MCP (Google Workspace)

```bash
mcporter config add google-workspace --command "npx" --arg "-y" --arg "@presto-ai/google-workspace-mcp" --scope home
mcporter config list
```

## 2.11 Включение ежедневного бэкапа

```bash
( crontab -l 2>/dev/null | grep -v "daily_kb_backup.sh"; echo "0 19 * * * /home/safeuser/.openclaw/workspace/scripts/daily_kb_backup.sh" ) | crontab -
crontab -l
```

## 2.12 Первый ручной тест бэкапа

```bash
bash /home/safeuser/.openclaw/workspace/scripts/daily_kb_backup.sh
```

Проверить в GitHub, что появился commit (и при необходимости тег дня).

## 2.13 Проверка структуры директорий (чек-лист)

```bash
ls -la /home/safeuser/.openclaw/workspace
ls -la /home/safeuser/.openclaw/workspace/scripts
ls -la /home/safeuser/.openclaw/workspace/skills
ls -la /home/safeuser/.mcporter
ls -la /home/safeuser/.config/google-workspace-mcp || true
```

## 2.14 Авторизация Google (когда понадобится)

При первом реальном вызове Google Workspace MCP откроется OAuth-процесс.  
Выполни любой вызов, например:

```bash
mcporter call --server google-workspace --tool "people.getMe"
```

Подтверди доступ в браузере.

---

## 3) Автоматический путь (одной командой)

Если репозиторий уже клонирован:

```bash
bash /home/safeuser/.openclaw/workspace/scripts/restore_openclaw.sh
```

Этот скрипт:
- ставит пакеты,
- ставит openclaw/clawhub/mcporter,
- подтягивает репозиторий,
- устанавливает скиллы,
- добавляет mcporter-конфиг,
- прописывает cron на 00:00 Екатеринбург.

---

## 4) Что НЕ хранится в GitHub (и как учесть)

Обычно не храним в git:
- локальные OAuth-токены (`~/.config/google-workspace-mcp`)
- приватные SSH-ключи (`~/.ssh/id_ed25519`)

После переезда на новый VPS их нужно заново создать/авторизовать.

---

## 5) Быстрый «минимум команд» для аварийного восстановления

```bash
sudo apt-get update && sudo apt-get install -y git curl build-essential libsecret-1-0 libsecret-1-dev
npm install -g openclaw clawhub mcporter
mkdir -p /home/safeuser/.openclaw
git clone git@github.com:GlazzEyezClazz/OpenCLaw.git /home/safeuser/.openclaw/workspace
cd /home/safeuser/.openclaw/workspace
clawhub login
clawhub install find-skills
clawhub install google-workspace-mcp --force
mcporter config add google-workspace --command "npx" --arg "-y" --arg "@presto-ai/google-workspace-mcp" --scope home
( crontab -l 2>/dev/null | grep -v "daily_kb_backup.sh"; echo "0 19 * * * /home/safeuser/.openclaw/workspace/scripts/daily_kb_backup.sh" ) | crontab -
```

---

Если что-то не сходится с этим документом, за эталон берём состояние `master` в GitHub-репозитории.
