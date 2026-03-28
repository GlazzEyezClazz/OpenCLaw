@echo off
echo === Universal Parser Setup ===

:: Проверяем Python
python --version >nul 2>&1 || (echo Python не найден! Установите Python 3.12+ && pause && exit)

:: Создаём виртуальное окружение
if not exist "venv" (
    echo Создаю виртуальное окружение...
    python -m venv venv
)

:: Активируем venv
call venv\Scripts\activate.bat

:: Устанавливаем зависимости
echo Устанавливаю зависимости...
pip install -r requirements.txt

:: Устанавливаем Playwright браузер
echo Устанавливаю Chromium для Playwright...
playwright install chromium

:: Копируем .env если нет
if not exist ".env" (
    copy .env.example .env
    echo Создан файл .env — заполните ANTHROPIC_API_KEY
)

echo.
echo === Готово! ===
echo Заполните .env файл (ANTHROPIC_API_KEY)
echo Запуск: venv\Scripts\activate && python server.py
pause
