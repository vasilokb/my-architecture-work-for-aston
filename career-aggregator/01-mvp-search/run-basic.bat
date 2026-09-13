@echo off
echo ========================================
echo Базовый запуск Career Aggregator 2
echo Без сложных зависимостей
echo ========================================
echo.

echo Шаг 1: Установка основных зависимостей
pip install fastapi uvicorn httpx loguru pydantic python-dotenv

echo.
echo Шаг 2: Создание .env файла
if not exist ".env" (
    copy .env.example .env
    echo Создан .env файл. При необходимости отредактируйте его.
)

echo.
echo Шаг 3: Запуск API сервера
echo API будет доступен по адресу: http://localhost:8000
echo.
echo Откройте новое окно PowerShell для Streamlit (шаг 4)
echo.
start powershell -NoExit -Command "cd /d '%~dp0' && python -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000"

echo.
echo Шаг 4: Установка Streamlit и запуск UI
echo Устанавливаем Streamlit...
pip install streamlit

echo.
echo Запускаем веб-интерфейс...
echo Интерфейс будет доступен по адресу: http://localhost:8501
echo.
timeout /t 3 /nobreak
start powershell -NoExit -Command "cd /d '%~dp0' && streamlit run app/ui/main.py --server.port 8501"

echo.
echo ========================================
echo Приложение запущено!
echo.
echo Проверьте работу:
echo 1. API: http://localhost:8000/api/health
echo 2. Веб-интерфейс: http://localhost:8501
echo.
echo Примечание: Некоторые функции могут быть ограничены
echo без установки дополнительных зависимостей.
echo.
echo Нажмите любую клавишу для закрытия этого окна...
pause >nul