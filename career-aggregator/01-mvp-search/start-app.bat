@echo off
echo ========================================
echo Запуск Career Aggregator 2
echo Используется виртуальное окружение
echo ========================================
echo.

echo 1. Активация виртуального окружения
call venv\Scripts\activate

echo.
echo 2. Проверка зависимостей
python -c "import fastapi; import uvicorn; import httpx; print('Зависимости установлены')"

echo.
echo 3. Запуск API сервера
echo API будет доступен по адресу: http://localhost:8000
echo Документация: http://localhost:8000/docs
echo.
echo Для остановки нажмите Ctrl+C
echo.

python -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

pause