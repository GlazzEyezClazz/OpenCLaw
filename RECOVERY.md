# Recovery / Восстановление OpenClaw после потери VPS

Ниже — короткая рабочая инструкция, как поднять всё заново на новом сервере.

## 0) Что уже настроено

- Бэкап уходит в GitHub: `git@github.com:GlazzEyezClazz/OpenCLaw.git`
- Ежедневный авто-бэкап по cron: **00:00 Asia/Yekaterinburg** (это `19:00 UTC`)
- Для откатов ставится ежедневный git tag: `backup-YYYY-MM-DD`

## 1) Поднять новый VPS

Рекомендуется Ubuntu 24.04+.

## 2) Подготовить доступ к GitHub

- Добавь SSH-ключ сервера в GitHub (Deploy key или в свой аккаунт)
- Проверь:

```bash
ssh -T git@github.com
```

## 3) Быстрое восстановление (авто-скрипт)

```bash
bash /home/safeuser/.openclaw/workspace/scripts/restore_openclaw.sh
```

Если workspace ещё не существует, сначала можно клонировать репозиторий куда угодно, затем запустить скрипт из него.

## 4) Что попросит сделать вручную

После скрипта:

```bash
clawhub login
```

И один раз Google OAuth через любой вызов `mcporter` (для google-workspace-mcp).

## 5) Проверить, что всё поднялось

```bash
crontab -l
clawhub list
mcporter config list
```

## 6) Как откатиться к предыдущей «сборке»

### Вариант A — по тегу дня (удобно)

```bash
git -C /home/safeuser/.openclaw/workspace tag -l "backup-*" --sort=-creatordate | head
# выбрать нужный тег
git -C /home/safeuser/.openclaw/workspace checkout backup-YYYY-MM-DD
```

### Вариант B — по коммиту

```bash
git -C /home/safeuser/.openclaw/workspace log --oneline --decorate -n 30
# выбрать коммит
git -C /home/safeuser/.openclaw/workspace checkout <commit_sha>
```

> Примечание: checkout тега/коммита переводит репозиторий в detached HEAD. Для постоянной работы лучше создать ветку:

```bash
git -C /home/safeuser/.openclaw/workspace switch -c restore-YYYYMMDD
```

## 7) Ручной путь (если без restore-скрипта)

```bash
sudo apt-get update
sudo apt-get install -y git curl build-essential libsecret-1-0 libsecret-1-dev
npm install -g openclaw clawhub mcporter

git clone git@github.com:GlazzEyezClazz/OpenCLaw.git /home/safeuser/.openclaw/workspace
cd /home/safeuser/.openclaw/workspace
clawhub login
clawhub install find-skills
clawhub install google-workspace-mcp --force
mcporter config add google-workspace --command "npx" --arg "-y" --arg "@presto-ai/google-workspace-mcp" --scope home
( crontab -l 2>/dev/null | grep -v "daily_kb_backup.sh"; echo "0 19 * * * /home/safeuser/.openclaw/workspace/scripts/daily_kb_backup.sh" ) | crontab -
```
