"""
Основной модуль FastAPI приложения Career Aggregator 2.

Этот модуль инициализирует FastAPI приложение, настраивает middleware,
CORS, и подключает все маршруты (endpoints).
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
import logging
from loguru import logger
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from app.core.config import settings, get_settings
from app.api.endpoints import search, health, filters, cache
from app.core.logging import setup_logging
from app.services.cache.redis_client import get_redis_client


# Настройка логирования
setup_logging()

# Контекстный менеджер для управления жизненным циклом приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управляет жизненным циклом приложения.
    
    Выполняется при запуске приложения:
    - Инициализация подключений (Redis, etc.)
    - Загрузка моделей (опционально)
    
    Выполняется при остановке:
    - Закрытие подключений
    - Очистка ресурсов
    """
    startup_time = time.time()
    
    # Инициализация при запуске
    logger.info(f"Запуск {settings.app_name} v{settings.app_version}")
    logger.info(f"Режим отладки: {settings.debug}")
    logger.info(f"Уровень логирования: {settings.log_level}")
    
    # Инициализация Redis (если кэширование включено)
    if settings.cache_enabled:
        try:
            redis_client = await get_redis_client()
            # Проверка подключения к Redis
            await redis_client.ping()
            logger.info(f"Подключение к Redis установлено: {settings.redis_host}:{settings.redis_port}")
        except Exception as e:
            logger.warning(f"Не удалось подключиться к Redis: {e}. Кэширование будет отключено.")
            settings.cache_enabled = False
    
    # Загрузка моделей эмбеддингов (может быть отложенной)
    logger.info("Приложение готово к работе")
    logger.info(f"Время запуска: {time.time() - startup_time:.2f} секунд")
    
    yield  # Приложение работает
    
    # Очистка при остановке
    logger.info("Остановка приложения...")
    if settings.cache_enabled:
        try:
            redis_client = await get_redis_client()
            await redis_client.close()
            logger.info("Подключение к Redis закрыто")
        except Exception as e:
            logger.error(f"Ошибка при закрытии подключения к Redis: {e}")


# Создание экземпляра FastAPI приложения
app = FastAPI(
    title=settings.app_name,
    description="API для семантического поиска вакансий с интеграцией HH.ru",
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)

# Настройка middleware
# CORS middleware
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Trusted Host middleware (для безопасности в продакшене)
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"],  # В продакшене заменить на конкретные домены
    )

# Подключение маршрутов (endpoints)
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(filters.router, prefix="/api", tags=["filters"])
app.include_router(cache.router, prefix="/api", tags=["cache"])


# Глобальные обработчики исключений
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Обработчик HTTP исключений."""
    logger.warning(f"HTTP ошибка {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path,
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Обработчик общих исключений."""
    logger.error(f"Необработанное исключение: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Внутренняя ошибка сервера",
            "detail": str(exc) if settings.debug else "Обратитесь к администратору",
            "path": request.url.path,
        }
    )


# Кастомная документация OpenAPI
def custom_openapi():
    """Генерация кастомной OpenAPI схемы."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Кастомизация схемы
    openapi_schema["info"]["contact"] = {
        "name": "Career Aggregator Team",
        "email": "support@career-aggregator.example.com",
    }
    
    openapi_schema["info"]["license"] = {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }
    
    # Добавление тегов с описанием
    openapi_schema["tags"] = [
        {
            "name": "health",
            "description": "Проверка здоровья сервиса и метрики",
        },
        {
            "name": "search",
            "description": "Поиск вакансий и семантическое ранжирование",
        },
        {
            "name": "filters",
            "description": "Получение доступных фильтров и справочных данных",
        },
        {
            "name": "cache",
            "description": "Управление кэшем и статистика",
        },
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Корневой endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Корневой endpoint с информацией о API."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "description": "API для семантического поиска вакансий",
        "docs": "/docs" if settings.debug else "Документация отключена в продакшене",
        "endpoints": {
            "health": "/api/health",
            "search": "/api/search",
            "filters": "/api/filters",
            "cache_stats": "/api/cache/stats",
        }
    }


# Endpoint для проверки конфигурации (только в debug режиме)
@app.get("/config", include_in_schema=settings.debug)
async def get_config(current_settings: Settings = Depends(get_settings)):
    """Возвращает текущую конфигурацию (только в debug режиме)."""
    if not settings.debug:
        raise HTTPException(status_code=404, detail="Not Found")
    
    # Возвращаем конфигурацию без чувствительных данных
    config_summary = {
        "app": {
            "name": current_settings.app_name,
            "version": current_settings.app_version,
            "debug": current_settings.debug,
        },
        "hh_api": {
            "base_url": str(current_settings.hh_api_base_url),
            "user_agent_set": bool(current_settings.hh_user_agent and 
                                  current_settings.hh_user_agent != "CareerAggregator/1.0 (anonymous@example.com)"),
            "max_vacancies": current_settings.hh_max_vacancies_per_request,
        },
        "llm": {
            "enabled": bool(current_settings.deepseek_api_key),
            "model": current_settings.llm_model,
        },
        "cache": {
            "enabled": current_settings.cache_enabled,
            "redis_host": current_settings.redis_host,
            "redis_port": current_settings.redis_port,
        },
        "search": {
            "relevance_threshold": current_settings.relevance_threshold,
            "max_results": current_settings.max_results_to_return,
        }
    }
    
    return config_summary


if __name__ == "__main__":
    # Запуск приложения напрямую (для разработки)
    import uvicorn
    
    logger.info(f"Запуск сервера на {settings.api_host}:{settings.api_port}")
    uvicorn.run(
        "app.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        workers=settings.api_workers if not settings.debug else 1,
        log_level=settings.log_level.lower(),
    )