# Career Aggregator 2

Система семантического поиска вакансий с интеграцией HH.ru и использованием LLM для улучшения релевантности результатов.

## 🎯 Цель проекта

Создать MVP (минимально жизнеспособный продукт) для агрегации вакансий с HH.ru с улучшенным поиском через семантическое понимание запросов пользователей.

## ✨ Основные возможности

- **Семантический поиск**: понимание естественно-языковых запросов
- **Интеграция с HH.ru**: доступ к тысячам актуальных вакансий
- **LLM-парсинг**: автоматическое извлечение параметров из текстовых запросов
- **Векторное ранжирование**: сортировка результатов по релевантности
- **Веб-интерфейс**: удобный UI для поиска и фильтрации
- **Кэширование**: ускорение повторных запросов

## 🏗️ Архитектура

### Компоненты системы

1. **Streamlit UI** - веб-интерфейс для пользователей
2. **FastAPI Backend** - основной API сервис
3. **LLM Service** - парсинг запросов через DeepSeek API
4. **Embedding Service** - векторизация текста для семантического поиска
5. **Cache Service** - in-memory кэширование результатов
6. **HH.ru Integration** - клиент для API HH.ru

### Диаграммы архитектуры

- [Компонентная архитектура](components.puml)
- [Поток данных](flow.puml) 
- [Архитектура развертывания](deployment.puml)
- [Архитектурное видение](avd.md)

## 🚀 Быстрый старт

### Предварительные требования

- Docker и Docker Compose
- Python 3.11+ (для локальной разработки)
- API ключ DeepSeek (опционально, для LLM функциональности)

### Запуск через Docker Compose

```bash
# Клонирование репозитория
git clone <repository-url>
cd career-aggregator-2

# Создание .env файла (на основе .env.example)
cp .env.example .env
# Отредактируйте .env файл при необходимости

# Запуск всех сервисов
docker-compose up -d

# Или используйте скрипт быстрого запуска
# Для Linux/macOS:
chmod +x scripts/quick_start.sh
./scripts/quick_start.sh

# Для Windows:
scripts\quick_start.bat

# Копирование конфигурации окружения
cp .env.example .env
# Редактирование .env при необходимости

# Запуск всех сервисов
docker-compose up -d
```

После запуска откройте в браузере:
- Веб-интерфейс: http://localhost:8501
- API документация: http://localhost:8000/docs
- Мониторинг Redis: http://localhost:8081 (если включен)

### Локальная разработка

```bash
# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt

# Запуск сервисов
python -m streamlit run app/ui.py  # Веб-интерфейс
python -m uvicorn app.api:app --reload  # API сервер
```

## 📋 Функциональность

### Поиск вакансий

1. **Текстовый запрос**: пользователь вводит запрос на естественном языке
   - Пример: "системный аналитик, минск, сеньор"
   - Пример: "удаленная работа python разработчик"

2. **LLM-парсинг**: система анализирует запрос и извлекает параметры:
   - Профессия/должность
   - Локация (город, регион)
   - Уровень опыта (junior, middle, senior)
   - Тип занятости (удаленная, офис, гибрид)

3. **Поиск в HH.ru**: формирование API запроса с извлеченными параметрами

4. **Семантическое ранжирование**: векторизация и сортировка по релевантности

5. **Отображение результатов**: список вакансий с ключевой информацией

### Фильтры (опционально)

- Город/регион
- Уровень опыта
- График работы
- Зарплатная вилка
- Тип занятости

## 🔧 Технологический стек

### Бэкенд
- **Python 3.11+** - основной язык разработки
- **FastAPI** - веб-фреймворк для API
- **Sentence-Transformers** - модели для эмбеддингов
- **Redis** - кэширование (in-memory)
- **Pydantic** - валидация данных
- **HTTPX** - асинхронные HTTP клиенты

### Фронтенд
- **Streamlit** - фреймворк для веб-интерфейса
- **Pandas** - обработка данных для отображения
- **Plotly** - визуализации (опционально)

### Внешние сервисы
- **HH.ru API** - источник данных о вакансиях
- **DeepSeek API** - LLM для парсинга запросов

### Инфраструктура
- **Docker** - контейнеризация
- **Docker Compose** - оркестрация сервисов
- **Nginx** - reverse proxy (опционально)
- **Prometheus/Grafana** - мониторинг (опционально)

## 📁 Структура проекта

```
career-aggregator-2/
├── app/                    # Основной код приложения
│   ├── api/               # FastAPI endpoints
│   ├── core/              # Бизнес-логика
│   ├── services/          # Сервисы (LLM, embeddings, cache)
│   ├── models/            # Pydantic модели
│   ├── utils/             # Вспомогательные функции
│   └── ui.py              # Streamlit интерфейс
├── tests/                 # Тесты
├── docs/                  # Документация
├── docker/                # Docker конфигурации
├── docker-compose.yml     # Оркестрация контейнеров
├── requirements.txt       # Зависимости Python
├── .env.example          # Шаблон переменных окружения
├── README.md             # Этот файл
└── архитектурные файлы:
    ├── avd.md            # Архитектурное видение
    ├── components.puml   # Диаграмма компонентов
    ├── flow.puml         # Диаграмма потока данных
    └── deployment.puml   # Диаграмма развертывания
```

## 🔌 API Endpoints

### Основные endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/health` | Проверка здоровья сервиса |
| POST | `/api/search` | Поиск вакансий по запросу |
| GET | `/api/filters` | Получение доступных фильтров |
| GET | `/api/cache/stats` | Статистика кэша |

### Пример запроса поиска

```bash
curl -X POST "http://localhost:8000/api/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "системный аналитик, минск",
    "filters": {
      "experience": "between3And6",
      "schedule": "remote"
    },
    "limit": 50
  }'
```

### Пример ответа

```json
{
  "query": "системный аналитик, минск",
  "total_results": 245,
  "returned_results": 50,
  "vacancies": [
    {
      "id": "123456",
      "title": "Системный аналитик",
      "company": "IT-компания",
      "salary": {"from": 150000, "to": 200000, "currency": "RUR"},
      "location": "Минск",
      "experience": "3-6 лет",
      "schedule": "Удаленная работа",
      "description": "Требуется системный аналитик для работы с ERP системами...",
      "skills": ["BPMN", "UML", "SQL", "API"],
      "url": "https://hh.ru/vacancy/123456",
      "relevance_score": 0.87
    }
  ],
  "search_params": {
    "profession": "системный аналитик",
    "location": "минск",
    "experience": "between3And6"
  }
}
```

## ⚙️ Конфигурация

### Переменные окружения

Создайте файл `.env` на основе `.env.example`:

```env
# HH.ru API настройки
HH_API_BASE_URL=https://api.hh.ru
HH_USER_AGENT=CareerAggregator/1.0 (your-email@example.com)

# LLM настройки
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_API_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

# Embeddings настройки
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DEVICE=cpu  # или cuda если есть GPU

# Redis настройки
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_CACHE_TTL=3600  # 1 час в секундах

# FastAPI настройки
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Streamlit настройки
STREAMLIT_HOST=0.0.0.0
STREAMLIT_PORT=8501
```

### Конфигурация Docker

Основные сервисы в `docker-compose.yml`:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  api:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - redis
    environment:
      - REDIS_HOST=redis

  streamlit:
    build: .
    ports:
      - "8501:8501"
    depends_on:
      - api
    command: streamlit run app/ui.py

  # Опционально: мониторинг Redis
  redis-commander:
    image: rediscommander/redis-commander:latest
    ports:
      - "8081:8081"
    depends_on:
      - redis
    environment:
      - REDIS_HOSTS=local:redis:6379
```

## 🧪 Тестирование

### Запуск тестов

```bash
# Установка тестовых зависимостей
pip install -r requirements-test.txt

# Запуск всех тестов
pytest tests/ -v

# Запуск с покрытием кода
pytest tests/ --cov=app --cov-report=html
```

### Типы тестов

- **Unit тесты**: тестирование отдельных функций и классов
- **Integration тесты**: тестирование взаимодействия компонентов
- **API тесты**: тестирование endpoints через HTTP
- **E2E тесты**: полные сценарии использования (опционально)

## 📊 Мониторинг и логирование

### Метрики

Система предоставляет метрики для мониторинга:

- Время ответа API
- Hit rate кэша
- Количество запросов к HH.ru API
- Ошибки и исключения
- Использование памяти и CPU

### Логи

Логирование настроено через структурированные логи (JSON формат):

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "service": "api",
  "endpoint": "/api/search",
  "query": "python разработчик",
  "duration_ms": 1250,
  "cache_hit": true,
  "results_count": 42
}
```

## 🔄 Развертывание

### Локальная разработка

```bash
docker-compose up --build
```

### Продакшен (пример для AWS)

```bash
# Сборка и публикация образов
docker build -t career-aggregator:latest .
docker tag career-aggregator:latest registry.example.com/career-aggregator:latest
docker push registry.example.com/career-aggregator:latest

# Развертывание в ECS/Kubernetes
# (конфигурация зависит от выбранной платформы)
```

### CI/CD Pipeline

Пример конфигурации GitHub Actions:

```yaml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to production
        run: |
          # Скрипт развертывания
```

## 🤝 Вклад в проект

### Установка для разработки

1. Форкните репозиторий
2. Клонируйте ваш форк
3. Создайте ветку для фичи/багфикса
4. Установите зависимости разработки
5. Внесите изменения
6. Напишите тесты
7. Создайте Pull Request

### Стиль кода

- Используйте **black** для форматирования
- Проверяйте код с помощью **flake8**
- Типизация с помощью **mypy**
- Документируйте публичные функции и классы

### Коммиты

Используйте [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: добавить поддержку новых фильтров
fix: исправить пагинацию при пустом результате
docs: обновить README с примерами API
test: добавить тесты для кэширования
chore: обновить зависимости
```

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл [LICENSE](LICENSE) для подробностей.

## 📞 Контакты и поддержка

- **Issues**: [GitHub Issues](https://github.com/your-username/career-aggregator-2/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/career-aggregator-2/discussions)
- **Email**: ваш-email@example.com

---

*Последнее обновление: 2026-03-29*  
*Версия проекта: 0.1.0 (MVP)*