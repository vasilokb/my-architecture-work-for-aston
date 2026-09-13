"""
Endpoints для управления кэшем и получения статистики.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from app.core.config import settings
from app.services.cache import get_redis_client, RedisCache
from app.models.hh import CacheStats


router = APIRouter()


@router.get("/cache/stats", response_model=CacheStats)
async def get_cache_stats(
    redis_client: RedisCache = Depends(get_redis_client),
) -> CacheStats:
    """
    Возвращает статистику использования кэша.
    
    Включает:
    - Количество попаданий (hits) и промахов (misses)
    - Hit rate (процент попаданий)
    - Размер кэша в памяти
    - Среднее время жизни записей (TTL)
    """
    logger.info("Запрос статистики кэша")
    
    if not redis_client.enabled:
        raise HTTPException(
            status_code=400,
            detail="Кэширование отключено в настройках"
        )
    
    try:
        stats = await redis_client.get_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики кэша: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении статистики кэша: {str(e)}"
        )


@router.post("/cache/clear")
async def clear_cache(
    pattern: str = "*",
    redis_client: RedisCache = Depends(get_redis_client),
) -> Dict[str, Any]:
    """
    Очищает кэш по указанному паттерну.
    
    Параметры:
    - pattern: Паттерн ключей для удаления (по умолчанию "*" - все ключи)
    
    Возвращает:
    - Количество удаленных ключей
    """
    if not settings.debug:
        raise HTTPException(
            status_code=403,
            detail="Очистка кэша доступна только в debug режиме"
        )
    
    if not redis_client.enabled:
        raise HTTPException(
            status_code=400,
            detail="Кэширование отключено в настройках"
        )
    
    logger.warning(f"Очистка кэша по паттерну: {pattern}")
    
    try:
        deleted_count = await redis_client.clear(pattern)
        
        return {
            "status": "success",
            "message": f"Кэш очищен по паттерну: {pattern}",
            "deleted_keys": deleted_count,
        }
        
    except Exception as e:
        logger.error(f"Ошибка при очистке кэша: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при очистке кэша: {str(e)}"
        )


@router.delete("/cache/key/{key}")
async def delete_cache_key(
    key: str,
    redis_client: RedisCache = Depends(get_redis_client),
) -> Dict[str, Any]:
    """
    Удаляет конкретный ключ из кэша.
    
    Параметры:
    - key: Ключ для удаления
    
    Возвращает:
    - Статус операции
    """
    if not settings.debug:
        raise HTTPException(
            status_code=403,
            detail="Удаление ключей кэша доступно только в debug режиме"
        )
    
    if not redis_client.enabled:
        raise HTTPException(
            status_code=400,
            detail="Кэширование отключено в настройках"
        )
    
    logger.info(f"Удаление ключа из кэша: {key}")
    
    try:
        deleted = await redis_client.delete(key)
        
        if deleted:
            return {
                "status": "success",
                "message": f"Ключ удален: {key}",
            }
        else:
            return {
                "status": "not_found",
                "message": f"Ключ не найден: {key}",
            }
        
    except Exception as e:
        logger.error(f"Ошибка при удалении ключа из кэша: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при удалении ключа из кэша: {str(e)}"
        )


@router.get("/cache/info")
async def get_cache_info(
    redis_client: RedisCache = Depends(get_redis_client),
) -> Dict[str, Any]:
    """
    Возвращает информацию о конфигурации кэша.
    
    Включает:
    - Статус кэширования (включено/выключено)
    - Конфигурацию Redis
    - Текущие настройки TTL
    """
    logger.info("Запрос информации о кэше")
    
    cache_info = {
        "enabled": redis_client.enabled,
        "configuration": {
            "redis_url": redis_client.redis_url if redis_client.enabled else None,
            "ttl_seconds": redis_client.ttl,
            "max_entries": redis_client.max_entries,
        },
        "settings": {
            "cache_enabled": settings.cache_enabled,
            "redis_host": settings.redis_host,
            "redis_port": settings.redis_port,
            "redis_cache_ttl": settings.redis_cache_ttl,
            "redis_max_entries": settings.redis_max_entries,
        }
    }
    
    # Добавляем информацию о подключении
    if redis_client.enabled and redis_client.client:
        try:
            # Получаем базовую информацию о Redis
            info = await redis_client.client.info()
            
            cache_info["redis_info"] = {
                "version": info.get("redis_version"),
                "mode": info.get("redis_mode"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "total_connections_received": info.get("total_connections_received"),
                "total_commands_processed": info.get("total_commands_processed"),
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении информации о Redis: {e}")
            cache_info["redis_info"] = {"error": str(e)}
    
    return cache_info


@router.get("/cache/keys")
async def get_cache_keys(
    pattern: str = "*",
    limit: int = 100,
    redis_client: RedisCache = Depends(get_redis_client),
) -> Dict[str, Any]:
    """
    Возвращает список ключей в кэше по указанному паттерну.
    
    Параметры:
    - pattern: Паттерн для поиска ключей (по умолчанию "*")
    - limit: Максимальное количество ключей для возврата
    
    Возвращает:
    - Список ключей
    - Общее количество ключей
    """
    if not settings.debug:
        raise HTTPException(
            status_code=403,
            detail="Просмотр ключей кэша доступен только в debug режиме"
        )
    
    if not redis_client.enabled:
        raise HTTPException(
            status_code=400,
            detail="Кэширование отключено в настройках"
        )
    
    try:
        keys = await redis_client.client.keys(pattern)
        
        # Ограничиваем количество возвращаемых ключей
        if len(keys) > limit:
            keys = keys[:limit]
        
        # Получаем TTL для каждого ключа
        keys_with_info = []
        for key in keys:
            try:
                ttl = await redis_client.client.ttl(key)
                key_type = await redis_client.client.type(key)
                
                keys_with_info.append({
                    "key": key.decode('utf-8') if isinstance(key, bytes) else key,
                    "ttl": ttl,
                    "type": key_type,
                })
            except Exception:
                # Если не удалось получить информацию о ключе
                keys_with_info.append({
                    "key": key.decode('utf-8') if isinstance(key, bytes) else key,
                    "ttl": None,
                    "type": None,
                })
        
        return {
            "pattern": pattern,
            "total_keys": len(keys),
            "returned_keys": len(keys_with_info),
            "keys": keys_with_info,
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении ключей кэша: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении ключей кэша: {str(e)}"
        )


@router.post("/cache/warmup")
async def warmup_cache(
    redis_client: RedisCache = Depends(get_redis_client),
    hh_client: HHClient = Depends(get_hh_client),
) -> Dict[str, Any]:
    """
    Прогревает кэш популярными запросами.
    
    Загружает в кэш:
    - Популярные фильтры
    - Результаты популярных поисковых запросов
    """
    if not settings.debug:
        raise HTTPException(
            status_code=403,
            detail="Прогрев кэша доступен только в debug режиме"
        )
    
    if not redis_client.enabled:
        raise HTTPException(
            status_code=400,
            detail="Кэширование отключено в настройках"
        )
    
    logger.info("Прогрев кэша")
    
    try:
        warmup_results = {
            "filters_loaded": 0,
            "search_results_loaded": 0,
            "total_operations": 0,
        }
        
        # Прогреваем фильтры
        try:
            areas = await hh_client.get_areas()
            specializations = await hh_client.get_specializations()
            industries = await hh_client.get_industries()
            schedules = await hh_client.get_schedules()
            experience_levels = await hh_client.get_experience_levels()
            
            filters_data = {
                "areas": areas,
                "specializations": specializations,
                "industries": industries,
                "schedules": schedules,
                "experience_levels": experience_levels,
            }
            
            await redis_client.set("filters:all", filters_data, ttl=86400)
            warmup_results["filters_loaded"] = 1
            warmup_results["total_operations"] += 1
            
        except Exception as e:
            logger.error(f"Ошибка при прогреве фильтров: {e}")
        
        # Прогреваем популярные поисковые запросы
        popular_queries = [
            "python разработчик",
            "системный аналитик",
            "тестировщик",
            "менеджер проекта",
            "дизайнер",
        ]
        
        for query in popular_queries:
            try:
                # Ищем вакансии
                from app.models.hh import VacancySearchParams
                search_params = VacancySearchParams(text=query)
                search_response = await hh_client.search_vacancies(
                    params=search_params,
                    limit=20,
                )
                
                # Сохраняем в кэш
                await redis_client.cache_search_result(
                    query=query,
                    filters=None,
                    result=search_response,
                )
                
                warmup_results["search_results_loaded"] += 1
                warmup_results["total_operations"] += 1
                
            except Exception as e:
                logger.error(f"Ошибка при прогреве запроса '{query}': {e}")
        
        return {
            "status": "success",
            "message": "Кэш прогрет",
            "results": warmup_results,
        }
        
    except Exception as e:
        logger.error(f"Ошибка при прогреве кэша: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при прогреве кэша: {str(e)}"
        )