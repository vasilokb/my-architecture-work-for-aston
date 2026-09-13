@echo off
echo ========================================
echo Запуск Career Aggregator 2 (упрощенный)
echo ========================================
echo.

echo Шаг 1: Проверка Python
python --version
if errorlevel 1 (
    echo Ошибка: Python не установлен или не добавлен в PATH
    pause
    exit /b 1
)

echo.
echo Шаг 2: Установка минимальных зависимостей
echo Устанавливаем FastAPI и Uvicorn...
pip install fastapi uvicorn[standard] python-multipart httpx

echo.
echo Устанавливаем Streamlit...
pip install streamlit pandas

echo.
echo Устанавливаем остальные зависимости...
pip install loguru pydantic pydantic-settings python-dotenv tenacity aiofiles python-dateutil

echo.
echo Шаг 3: Создание .env файла (если отсутствует)
if not exist ".env" (
    echo Создаем .env файл из примера...
    copy .env.example .env
    echo ВНИМАНИЕ: Отредактируйте .env файл для настройки приложения
)

echo.
echo Шаг 4: Запуск FastAPI сервера
echo Запускаем API сервер на http://localhost:8000
echo Откройте новое окно PowerShell для следующего шага!
echo.
start powershell -NoExit -Command "cd /d '%~dp0' && python -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000"

echo.
echo Шаг 5: Запуск Streamlit интерфейса
echo Запускаем веб-интерфейс на http://localhost:8501
echo.
timeout /t 5 /nobreak
start powershell -NoExit -Command "cd /d '%~dp0' && streamlit run app/ui/main.py --server.port 8501"

echo.
echo ========================================
echo Приложение запускается!
echo.
echo API:      http://localhost:8000/api/health
echo Интерфейс: http://localhost:8501
echo.
echo Нажмите любую клавишу для завершения этого окна...
pause >nul