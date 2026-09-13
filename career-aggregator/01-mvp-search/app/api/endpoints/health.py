"""
Health check endpoints для мониторинга состояния сервиса.
"""

import time
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from app.core.config import settings, get_settings
from app.services.cache import get_redis_client, RedisCache
from app.services.hh import get_hh_client, HHClient
from app.services.embeddings import get_embedding_service, EmbeddingService
from app.services.llm import get_llm_service, LLMService


router = APIRouter()


@router.get("/health")
async def health_check(
    settings = Depends(get_settings),
    redis_client: RedisCache = Depends(get_redis_client),
    hh_client: HHClient = Depends(get_hh_client),
) -> Dict[str, Any]:
    """
    Проверка здоровья сервиса.
    
    Возвращает:
    - Статус сервиса
    - Версию приложения
    - Статус зависимостей (Redis, HH.ru API)
    - Время работы
    """
    start_time = time.time()
    
    health_data = {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": {},
    }
    
    # Проверка Redis
    try:
        if redis_client.enabled and redis_client.client:
            await redis_client.client.ping()
            health_data["dependencies"]["redis"] = {
                "status": "healthy",
                "enabled": True,
            }
        else:
            health_data["dependencies"]["redis"] = {
                "status": "disabled",
                "enabled": False,
            }
    except Exception as e:
        logger.error(f"Ошибка проверки Redis: {e}")
        health_data["dependencies"]["redis"] = {
            "status": "unhealthy",
            "error": str(e),
            "enabled": redis_client.enabled,
        }
        health_data["status"] = "degraded"
    
    # Проверка HH.ru API (упрощенная)
    try:
        # Простой запрос для проверки доступности API
        areas = await hh_client.get_areas()
        health_data["dependencies"]["hh_api"] = {
            "status": "healthy",
            "areas_count": len(areas) if areas else 0,
        }
    except Exception as e:
        logger.error(f"Ошибка проверки HH.ru API: {e}")
        health_data["dependencies"]["hh_api"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health_data["status"] = "degraded"
    
    # Проверка Embedding Service
    try:
        embedding_service = await get_embedding_service()
        test_embedding = await embedding_service.encode_text("тестовый текст")
        health_data["dependencies"]["embeddings"] = {
            "status": "healthy",
            "model": embedding_service.model_name,
            "dimension": len(test_embedding),
        }
    except Exception as e:
        logger.error(f"Ошибка проверки Embedding Service: {e}")
        health_data["dependencies"]["embeddings"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health_data["status"] = "degraded"
    
    # Проверка LLM Service
    try:
        llm_service = await get_llm_service()
        if llm_service.api_key:
            # Только проверяем наличие API ключа, не делаем реальный запрос
            health_data["dependencies"]["llm"] = {
                "status": "healthy",
                "model": llm_service.model,
                "api_key_configured": True,
            }
        else:
            health_data["dependencies"]["llm"] = {
                "status": "disabled",
                "api_key_configured": False,
            }
    except Exception as e:
        logger.error(f"Ошибка проверки LLM Service: {e}")
        health_data["dependencies"]["llm"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health_data["status"] = "degraded"
    
    # Добавляем метрики производительности
    health_data["performance"] = {
        "response_time_ms": (time.time() - start_time) * 1000,
        "debug_mode": settings.debug,
        "log_level": settings.log_level,
    }
    
    # Добавляем информацию о кэше
    if redis_client.enabled:
        try:
            cache_stats = await redis_client.get_stats()
            health_data["cache"] = {
                "hits": cache_stats.hits,
                "misses": cache_stats.misses,
                "hit_rate": cache_stats.hit_rate,
                "size_bytes": cache_stats.size,
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики кэша: {e}")
            health_data["cache"] = {"error": str(e)}
    
    return health_data


@router.get("/health/liveness")
async def liveness_probe() -> Dict[str, Any]:
    """
    Liveness probe для Kubernetes/оркестраторов.
    
    Простая проверка, что приложение запущено и отвечает.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/readiness")
async def readiness_probe(
    redis_client: RedisCache = Depends(get_redis_client),
) -> Dict[str, Any]:
    """
    Readiness probe для Kubernetes/оркестраторов.
    
    Проверяет, что приложение готово принимать трафик.
    """
    readiness_data = {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {},
    }
    
    # Проверка Redis (если включен)
    if redis_client.enabled:
        try:
            if redis_client.client:
                await redis_client.client.ping()
                readiness_data["checks"]["redis"] = "ready"
            else:
                readiness_data["checks"]["redis"] = "not_connected"
                readiness_data["status"] = "not_ready"
        except Exception as e:
            readiness_data["checks"]["redis"] = f"error: {str(e)}"
            readiness_data["status"] = "not_ready"
    
    # Проверка Embedding Service
    try:
        embedding_service = await get_embedding_service()
        if embedding_service.model is not None:
            readiness_data["checks"]["embeddings"] = "ready"
        else:
            readiness_data["checks"]["embeddings"] = "model_not_loaded"
            readiness_data["status"] = "not_ready"
    except Exception as e:
        readiness_data["checks"]["embeddings"] = f"error: {str(e)}"
        readiness_data["status"] = "not_ready"
    
    return readiness_data


@router.get("/health/metrics")
async def metrics_endpoint(
    redis_client: RedisCache = Depends(get_redis_client),
) -> Dict[str, Any]:
    """
    Возвращает метрики приложения для мониторинга.
    """
    metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "app": {
            "name": settings.app_name,
            "version": settings.app_version,
            "debug": settings.debug,
        },
        "cache": {},
        "requests": {},
    }
    
    # Статистика кэша
    if redis_client.enabled:
        try:
            cache_stats = await redis_client.get_stats()
            metrics["cache"] = {
                "hits": cache_stats.hits,
                "misses": cache_stats.misses,
                "total": cache_stats.total,
                "hit_rate": cache_stats.hit_rate,
                "hit_rate_percentage": cache_stats.hit_rate_percentage,
                "size_bytes": cache_stats.size,
                "avg_ttl_seconds": cache_stats.avg_ttl,
            }
        except Exception as e:
            metrics["cache"] = {"error": str(e)}
    
    # Счетчики запросов (пример - можно расширить)
    try:
        search_requests = await redis_client.get_counter("metrics:search_requests")
        successful_searches = await redis_client.get_counter("metrics:successful_searches")
        failed_searches = await redis_client.get_counter("metrics:failed_searches")
        
        metrics["requests"] = {
            "search_requests": search_requests,
            "successful_searches": successful_searches,
            "failed_searches": failed_searches,
            "success_rate": (
                successful_searches / search_requests 
                if search_requests > 0 else 0.0
            ),
        }
    except Exception:
        # Если счетчики не настроены, игнорируем
        pass
    
    return metrics


@router.get("/health/config")
async def config_endpoint(
    settings = Depends(get_settings),
) -> Dict[str, Any]:
    """
    Возвращает конфигурацию приложения (без чувствительных данных).
    
    Только в debug режиме.
    """
    if not settings.debug:
        raise HTTPException(
            status_code=403,
            detail="Config endpoint доступен только в debug режиме"
        )
    
    config_summary = {
        "app": {
            "name": settings.app_name,
            "version": settings.app_version,
            "debug": settings.debug,
            "log_level": settings.log_level,
        },
        "hh_api": {
            "base_url": str(settings.hh_api_base_url),
            "user_agent_configured": bool(
                settings.hh_user_agent and 
                settings.hh_user_agent != "CareerAggregator/1.0 (anonymous@example.com)"
            ),
            "max_vacancies": settings.hh_max_vacancies_per_request,
            "page_size": settings.hh_page_size,
        },
        "llm": {
            "api_key_configured": bool(settings.deepseek_api_key),
            "model": settings.llm_model,
            "temperature": settings.llm_temperature,
        },
        "embeddings": {
            "model": settings.embedding_model,
            "device": settings.embedding_device,
            "dimension": settings.embedding_dimension,
        },
        "cache": {
            "enabled": settings.cache_enabled,
            "redis_host": settings.redis_host,
            "redis_port": settings.redis_port,
            "ttl_seconds": settings.redis_cache_ttl,
        },
        "search": {
            "relevance_threshold": settings.relevance_threshold,
            "max_results": settings.max_results_to_return,
        },
        "api": {
            "host": settings.api_host,
            "port": settings.api_port,
            "workers": settings.api_workers,
        },
        "streamlit": {
            "host": settings.streamlit_host,
            "port": settings.streamlit_port,
            "theme": settings.streamlit_theme,
        },
    }
    
    return config_summary


@router.post("/health/reset-counters")
async def reset_counters(
    redis_client: RedisCache = Depends(get_redis_client),
) -> Dict[str, Any]:
    """
    Сбрасывает счетчики метрик.
    
    Только в debug режиме.
    """
    if not settings.debug:
        raise HTTPException(
            status_code=403,
            detail="Reset counters endpoint доступен только в debug режиме"
        )
    
    try:
        # Сбрасываем счетчики запросов
        counters = [
            "metrics:search_requests",
            "metrics:successful_searches",
            "metrics:failed_searches",
        ]
        
        for counter in counters:
            await redis_client.delete(counter)
        
        return {
            "status": "success",
            "message": "Счетчики сброшены",
            "counters_reset": counters,
        }
        
    except Exception as e:
        logger.error(f"Ошибка при сбросе счетчиков: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при сбросе счетчиков: {str(e)}"
        )