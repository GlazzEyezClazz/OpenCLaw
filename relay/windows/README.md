# VPS-only OpenClaw + local Chrome relay (Windows)

Цель: OpenClaw живёт на VPS, а локальный Chrome автоматически доступен агенту без ручного шаманства.

## Что уже сделано на VPS
- gateway bind включён для удалённого node host
- rate limit на auth включён

## 1) Подготовка SSH-ключа (один раз)
В PowerShell/CMD на ноуте:

```cmd
ssh-keygen -t ed25519 -f %USERPROFILE%\.ssh\openclaw_vps -N ""
type %USERPROFILE%\.ssh\openclaw_vps.pub | ssh safeuser@216.57.105.44 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

Проверь вход без пароля:

```cmd
ssh -i %USERPROFILE%\.ssh\openclaw_vps safeuser@216.57.105.44 "echo ok"
```

## 2) Запуск туннеля (порт VPS gateway = 18792)

```cmd
ssh -i %USERPROFILE%\.ssh\openclaw_vps -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L 18792:127.0.0.1:18792 safeuser@216.57.105.44
```

## 3) Запуск node host (в другом окне)

```cmd
set OPENCLAW_GATEWAY_URL=ws://127.0.0.1:18792
set OPENCLAW_GATEWAY_TOKEN=5b6894970cae4c485efd6470476e5f0551882c1aa00060fc
openclaw node run --host 127.0.0.1 --port 18792
```

## 4) Расширение OpenClaw Browser Relay
- Port: `18795`
- Gateway token: тот же
- Save
- На нужной вкладке клик иконки -> ON

## 5) Автозапуск при логине (Task Scheduler)
Создать 2 задачи (с highest privileges):

### tunnel
Program/script:
`C:\Windows\System32\OpenSSH\ssh.exe`

Add arguments:
`-i C:\Users\%USERNAME%\.ssh\openclaw_vps -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L 18792:127.0.0.1:18792 safeuser@216.57.105.44`

### nodehost
Program/script:
`C:\Windows\System32\cmd.exe`

Add arguments:
`/c set OPENCLAW_GATEWAY_URL=ws://127.0.0.1:18792 && set OPENCLAW_GATEWAY_TOKEN=5b6894970cae4c485efd6470476e5f0551882c1aa00060fc && openclaw node run --host 127.0.0.1 --port 18792`

Delay nodehost task by 20-30 sec after logon.

## 6) Проверка
- `openclaw node run` не падает
- в agent `nodes status` показывает connected=true
- extension показывает ON на вкладке
