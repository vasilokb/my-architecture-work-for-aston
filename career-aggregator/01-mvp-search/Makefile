# Makefile для Career Aggregator 2

.PHONY: help install dev test docker-up docker-down docker-build docker-logs clean

# Цвета для вывода
GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m # No Color

# Переменные
PYTHON = python
PIP = pip
DOCKER = docker
DOCKER_COMPOSE = docker-compose
VENV = venv
REQUIREMENTS = requirements.txt

help: ## Показать справку по командам
	@echo "$(GREEN)Career Aggregator 2 - Система семантического поиска вакансий$(NC)"
	@echo ""
	@echo "$(YELLOW)Доступные команды:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

install: ## Установить зависимости Python
	@echo "$(YELLOW)Установка зависимостей Python...$(NC)"
	$(PIP) install -r $(REQUIREMENTS)
	@echo "$(GREEN)Зависимости установлены$(NC)"

dev: ## Запустить сервер разработки
	@echo "$(YELLOW)Запуск сервера разработки...$(NC)"
	uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

test: ## Запустить тесты
	@echo "$(YELLOW)Запуск тестов...$(NC)"
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term

test-unit: ## Запустить unit тесты
	@echo "$(YELLOW)Запуск unit тестов...$(NC)"
	pytest tests/unit/ -v

test-integration: ## Запустить integration тесты
	@echo "$(YELLOW)Запуск integration тестов...$(NC)"
	pytest tests/integration/ -v

test-full-flow: ## Запустить тест полного потока
	@echo "$(YELLOW)Запуск теста полного потока...$(NC)"
	$(PYTHON) scripts/test_full_flow.py

docker-up: ## Запустить все сервисы в Docker (одна команда)
	@echo "$(YELLOW)Запуск Docker контейнеров...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(GREEN)Создание .env файла из .env.example...$(NC)"; \
		cp .env.example .env; \
		echo "$(YELLOW)Отредактируйте .env файл для настройки параметров$(NC)"; \
	fi
	$(DOCKER_COMPOSE) -f docker-compose.simple.yml up -d
	@echo "$(GREEN)Сервисы запущены:$(NC)"
	@echo "  Streamlit UI:      http://localhost:8501"
	@echo "  FastAPI API:       http://localhost:8000"
	@echo "  API документация:  http://localhost:8000/docs"

docker-down: ## Остановить все Docker сервисы
	@echo "$(YELLOW)Остановка Docker контейнеров...$(NC)"
	$(DOCKER_COMPOSE) down

docker-build: ## Пересобрать Docker образы
	@echo "$(YELLOW)Пересборка Docker образов...$(NC)"
	$(DOCKER_COMPOSE) build --no-cache

docker-logs: ## Показать логи Docker контейнеров
	@echo "$(YELLOW)Логи Docker контейнеров:$(NC)"
	$(DOCKER_COMPOSE) logs -f

docker-logs-api: ## Показать логи API сервиса
	@echo "$(YELLOW)Логи API сервиса:$(NC)"
	$(DOCKER_COMPOSE) logs -f api

docker-logs-streamlit: ## Показать логи Streamlit
	@echo "$(YELLOW)Логи Streamlit:$(NC)"
	$(DOCKER_COMPOSE) logs -f streamlit

docker-logs-redis: ## Показать логи Redis
	@echo "$(YELLOW)Логи Redis:$(NC)"
	$(DOCKER_COMPOSE) logs -f redis

docker-restart: ## Перезапустить Docker контейнеры
	@echo "$(YELLOW)Перезапуск Docker контейнеров...$(NC)"
	$(DOCKER_COMPOSE) restart

docker-clean: ## Очистить Docker (контейнеры, образы, тома)
	@echo "$(YELLOW)Очистка Docker...$(NC)"
	$(DOCKER_COMPOSE) down -v --rmi all
	$(DOCKER) system prune -f

format: ## Форматировать код с помощью black и isort
	@echo "$(YELLOW)Форматирование кода...$(NC)"
	black app/ tests/ scripts/
	isort app/ tests/ scripts/

lint: ## Проверить код с помощью flake8 и mypy
	@echo "$(YELLOW)Проверка кода...$(NC)"
	flake8 app/ tests/ scripts/
	mypy app/

check: ## Запустить форматирование и проверку кода
	@echo "$(YELLOW)Запуск проверок кода...$(NC)"
	$(MAKE) format
	$(MAKE) lint

clean: ## Очистить кэш и временные файлы
	@echo "$(YELLOW)Очистка временных файлов...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Очистка завершена$(NC)"

setup-env: ## Настроить окружение (создать .env файл)
	@echo "$(YELLOW)Настройка окружения...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(GREEN)Создание .env файла из .env.example...$(NC)"; \
		cp .env.example .env; \
		echo "$(YELLOW)Отредактируйте .env файл для настройки параметров$(NC)"; \
	else \
		echo "$(YELLOW).env файл уже существует$(NC)"; \
	fi

init: setup-env install ## Инициализировать проект (установить зависимости и настроить окружение)
	@echo "$(GREEN)Проект инициализирован$(NC)"

run-streamlit: ## Запустить Streamlit интерфейс локально
	@echo "$(YELLOW)Запуск Streamlit интерфейса...$(NC)"
	streamlit run app/ui/main.py

health-check: ## Проверить здоровье системы
	@echo "$(YELLOW)Проверка здоровья системы...$(NC)"
	curl -f http://localhost:8000/api/health || echo "$(RED)API недоступен$(NC)"

search-test: ## Протестировать поиск
	@echo "$(YELLOW)Тестирование поиска...$(NC)"
	curl -X POST http://localhost:8000/api/search \
		-H "Content-Type: application/json" \
		-d '{"query": "python разработчик", "limit": 5}' | jq . || echo "$(RED)Ошибка поиска$(NC)"

cache-stats: ## Показать статистику кэша
	@echo "$(YELLOW)Статистика кэша:$(NC)"
	curl -f http://localhost:8000/api/cache/stats | jq . || echo "$(RED)Ошибка получения статистики$(NC)"

# Алиасы
up: docker-up
down: docker-down
build: docker-build
logs: docker-logs
restart: docker-restart
test-all: test
ci: check test ## Запустить CI pipeline (форматирование, линтинг, тесты)