@echo off
REM Скрипт быстрого запуска Career Aggregator 2 для Windows

echo 🚀 Запуск Career Aggregator 2...

REM Проверяем наличие .env файла
if not exist .env (
    echo 📝 Создание .env файла из .env.example...
    copy .env.example .env
    echo ⚠️  Отредактируйте .env файл для настройки параметров
)

REM Запускаем Docker Compose
echo 🐳 Запуск Docker контейнеров...
docker-compose up -d

if %ERRORLEVEL% neq 0 (
    echo ❌ Ошибка при запуске Docker Compose
    exit /b 1
)

echo ⏳ Ожидание запуска сервисов...

REM Ждем запуска Redis
echo 🔍 Ожидание запуска Redis...
timeout /t 5 /nobreak > nul

REM Ждем запуска API
echo 🔍 Ожидание запуска API...
set max_attempts=30
set attempt=1

:check_api
curl -s http://localhost:8000/api/health > nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo ✅ API запущен
    goto api_ready
)

if %attempt% equ %max_attempts% (
    echo ❌ API не запустился за отведенное время
    docker-compose logs api
    exit /b 1
)

set /a attempt+=1
timeout /t 2 /nobreak > nul
goto check_api

:api_ready
REM Ждем запуска Streamlit
echo 🔍 Ожидание запуска Streamlit...
set attempt=1

:check_streamlit
curl -s http://localhost:8501/_stcore/health > nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo ✅ Streamlit запущен
    goto streamlit_ready
)

if %attempt% equ 30 (
    echo ⚠️  Streamlit медленно запускается, продолжаем...
    goto streamlit_ready
)

set /a attempt+=1
timeout /t 2 /nobreak > nul
goto check_streamlit

:streamlit_ready
echo.
echo ✨ Система успешно запущена!
echo.
echo 🌐 Доступные сервисы:
echo    Streamlit UI:      http://localhost:8501
echo    FastAPI API:       http://localhost:8000
echo    API документация:  http://localhost:8000/docs
echo.
echo 🔧 Полезные команды:
echo    Просмотр логов:    docker-compose logs -f
echo    Остановка:         docker-compose down
echo    Перезапуск:        docker-compose restart
echo.
echo 🧪 Тестирование системы:
echo    python scripts/test_full_flow.py --quick

REM Запускаем быстрый тест
echo.
echo 🧪 Запуск быстрого теста...
python scripts/test_full_flow.py --quick

echo.
echo 🎉 Готово! Откройте http://localhost:8501 в браузере
pause