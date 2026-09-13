#!/bin/bash

# Скрипт быстрого запуска Career Aggregator 2

set -e

echo "🚀 Запуск Career Aggregator 2..."

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "📝 Создание .env файла из .env.example..."
    cp .env.example .env
    echo "⚠️  Отредактируйте .env файл для настройки параметров"
fi

# Запускаем Docker Compose
echo "🐳 Запуск Docker контейнеров..."
docker-compose up -d

echo "⏳ Ожидание запуска сервисов..."

# Ждем запуска Redis
echo "🔍 Ожидание запуска Redis..."
sleep 5

# Ждем запуска API
echo "🔍 Ожидание запуска API..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/health > /dev/null; then
        echo "✅ API запущен"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ API не запустился за отведенное время"
        docker-compose logs api
        exit 1
    fi
    sleep 2
done

# Ждем запуска Streamlit
echo "🔍 Ожидание запуска Streamlit..."
for i in {1..30}; do
    if curl -s http://localhost:8501/_stcore/health > /dev/null; then
        echo "✅ Streamlit запущен"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "⚠️  Streamlit медленно запускается, продолжаем..."
        break
    fi
    sleep 2
done

echo ""
echo "✨ Система успешно запущена!"
echo ""
echo "🌐 Доступные сервисы:"
echo "   Streamlit UI:      http://localhost:8501"
echo "   FastAPI API:       http://localhost:8000"
echo "   API документация:  http://localhost:8000/docs"
echo ""
echo "🔧 Полезные команды:"
echo "   Просмотр логов:    docker-compose logs -f"
echo "   Остановка:         docker-compose down"
echo "   Перезапуск:        docker-compose restart"
echo ""
echo "🧪 Тестирование системы:"
echo "   python scripts/test_full_flow.py --quick"

# Запускаем быстрый тест
echo ""
echo "🧪 Запуск быстрого теста..."
python scripts/test_full_flow.py --quick

echo ""
echo "🎉 Готово! Откройте http://localhost:8501 в браузере"