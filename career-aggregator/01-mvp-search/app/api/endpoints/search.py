"""
Search endpoints для поиска вакансий.
"""

import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from loguru import logger

from app.core.config import settings, get_settings
from app.core.logging import log_search_query
from app.services.cache import get_redis_client, RedisCache
from app.services.hh import get_hh_client, HHClient
from app.services.embeddings import get_embedding_service, EmbeddingService
from app.services.llm import get_llm_service, LLMService, LLMAPIError, LLMParsingError
from app.models.hh import (
    SemanticSearchRequest,
    SemanticSearchResponse,
    VacancySearchParams,
    ParsedQuery,
)


router = APIRouter()


@router.post("/search", response_model=SemanticSearchResponse)
async def search_vacancies(
    request: SemanticSearchRequest,
    background_tasks: BackgroundTasks,
    settings = Depends(get_settings),
    redis_client: RedisCache = Depends(get_redis_client),
    hh_client: HHClient = Depends(get_hh_client),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    llm_service: LLMService = Depends(get_llm_service),
) -> SemanticSearchResponse:
    """
    Поиск вакансий с семантическим ранжированием.
    
    Параметры:
    - query: Поисковый запрос на естественном языке
    - filters: Дополнительные фильтры (опционально)
    - limit: Максимальное количество результатов (по умолчанию 50)
    - use_semantic: Использовать семантическое ранжирование (по умолчанию True)
    
    Возвращает:
    - Отсортированный список вакансий с релевантностью
    - Параметры поиска
    - Статистику поиска
    """
    start_time = time.time()
    
    logger.info(f"Поисковый запрос: '{request.query}', limit: {request.limit}")
    
    # Шаг 1: Проверяем кэш
    cache_hit = False
    cached_result = None
    
    if redis_client.enabled:
        cached_result = await redis_client.get_search_result(
            query=request.query,
            filters=request.filters,
        )
        
        if cached_result:
            cache_hit = True
            logger.info(f"Кэш попадание для запроса: '{request.query}'")
            
            # Добавляем информацию о кэше
            cached_result.cache_hit = True
            cached_result.processing_time = (time.time() - start_time) * 1000
            
            # Логируем запрос
            log_search_query(
                query=request.query,
                results_count=cached_result.returned_results,
                cache_hit=True,
                duration=time.time() - start_time,
            )
            
            # Обновляем счетчики в фоне
            background_tasks.add_task(
                _update_search_metrics,
                redis_client,
                successful=True,
                cache_hit=True,
            )
            
            return cached_result
    
    # Шаг 2: Парсим запрос с помощью LLM
    parsed_query: Optional[ParsedQuery] = None
    search_params: Optional[VacancySearchParams] = None
    
    try:
        parsed_query = await llm_service.parse_query(request.query)
        search_params = parsed_query.to_search_params()
        
        logger.info(
            f"Запрос распарсен. "
            f"Профессия: {parsed_query.profession}, "
            f"Локация: {parsed_query.location}, "
            f"Опыт: {parsed_query.experience}"
        )
        
        # Сохраняем в кэш
        if redis_client.enabled:
            await redis_client.cache_parsed_query(
                query=request.query,
                parsed_query=parsed_query,
            )
            
    except (LLMAPIError, LLMParsingError) as e:
        logger.error(f"Ошибка парсинга запроса LLM: {type(e).__name__}: {e}")
        # Используем текстовый поиск без парсинга
        search_params = VacancySearchParams(text=request.query)
    except Exception as e:
        logger.error(f"Неожиданная ошибка при парсинге запроса: {type(e).__name__}: {e}")
        # Используем текстовый поиск без парсинга
        search_params = VacancySearchParams(text=request.query)
    
    # Шаг 3: Применяем дополнительные фильтры
    if request.filters:
        if search_params:
            # Обновляем параметры поиска фильтрами
            for key, value in request.filters.items():
                if hasattr(search_params, key):
                    setattr(search_params, key, value)
        else:
            search_params = VacancySearchParams(**request.filters)
    
    # Шаг 4: Ищем вакансии в HH.ru
    try:
        search_response = await hh_client.search_vacancies(
            params=search_params,
            limit=request.limit * 2,  # Ищем больше, чтобы после фильтрации осталось достаточно
        )
        
        logger.info(
            f"Найдено вакансий в HH.ru: {search_response.found}, "
            f"Получено: {len(search_response.vacancies)}"
        )
        
        if not search_response.vacancies:
            # Возвращаем пустой результат
            response = SemanticSearchResponse(
                query=request.query,
                total_results=0,
                returned_results=0,
                vacancies=[],
                search_params=search_params.dict() if search_params else None,
                cache_hit=False,
                processing_time=(time.time() - start_time) * 1000,
            )
            
            # Логируем запрос
            log_search_query(
                query=request.query,
                results_count=0,
                cache_hit=False,
                duration=time.time() - start_time,
            )
            
            # Обновляем счетчики в фоне
            background_tasks.add_task(
                _update_search_metrics,
                redis_client,
                successful=True,
                cache_hit=False,
            )
            
            return response
        
    except Exception as e:
        logger.error(f"Ошибка поиска в HH.ru: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка поиска в HH.ru: {str(e)}"
        )
    
    # Шаг 5: Семантическое ранжирование (если включено)
    ranked_vacancies = search_response.vacancies
    
    if request.use_semantic and embedding_service:
        try:
            ranked_vacancies = await embedding_service.rank_vacancies_by_relevance(
                query=request.query,
                vacancies=search_response.vacancies,
                threshold=settings.relevance_threshold,
            )
            
            logger.info(
                f"Семантическое ранжирование завершено. "
                f"После фильтрации: {len(ranked_vacancies)} вакансий"
            )
            
        except Exception as e:
            logger.error(f"Ошибка семантического ранжирования: {e}")
            # Продолжаем с несортированными результатами
    
    # Шаг 6: Ограничиваем количество результатов
    if request.limit and len(ranked_vacancies) > request.limit:
        ranked_vacancies = ranked_vacancies[:request.limit]
    
    # Шаг 7: Формируем ответ
    response = SemanticSearchResponse(
        query=request.query,
        total_results=search_response.found,
        returned_results=len(ranked_vacancies),
        vacancies=ranked_vacancies,
        search_params=search_params.dict() if search_params else None,
        cache_hit=False,
        processing_time=(time.time() - start_time) * 1000,
    )
    
    # Шаг 8: Сохраняем в кэш
    if redis_client.enabled and not cache_hit:
        await redis_client.cache_search_result(
            query=request.query,
            filters=request.filters,
            result=response,
        )
        logger.info(f"Результат поиска сохранен в кэш: '{request.query}'")
    
    # Шаг 9: Логируем запрос
    log_search_query(
        query=request.query,
        results_count=len(ranked_vacancies),
        cache_hit=False,
        duration=time.time() - start_time,
        semantic_used=request.use_semantic,
    )
    
    # Шаг 10: Обновляем счетчики в фоне
    background_tasks.add_task(
        _update_search_metrics,
        redis_client,
        successful=True,
        cache_hit=False,
    )
    
    logger.info(
        f"Поиск завершен. "
        f"Запрос: '{request.query}', "
        f"Результатов: {len(ranked_vacancies)}, "
        f"Время: {(time.time() - start_time) * 1000:.2f} мс"
    )
    
    return response


@router.post("/search/basic", response_model=SemanticSearchResponse)
async def search_vacancies_basic(
    request: SemanticSearchRequest,
    background_tasks: BackgroundTasks,
    hh_client: HHClient = Depends(get_hh_client),
    redis_client: RedisCache = Depends(get_redis_client),
) -> SemanticSearchResponse:
    """
    Базовый поиск вакансий без семантического ранжирования.
    
    Быстрее, но менее точный.
    """
    start_time = time.time()
    
    logger.info(f"Базовый поиск: '{request.query}'")
    
    # Проверяем кэш
    cache_hit = False
    if redis_client.enabled:
        cached_result = await redis_client.get_search_result(
            query=request.query,
            filters=request.filters,
        )
        
        if cached_result:
            cache_hit = True
            cached_result.cache_hit = True
            cached_result.processing_time = (time.time() - start_time) * 1000
            
            # Логируем запрос
            log_search_query(
                query=request.query,
                results_count=cached_result.returned_results,
                cache_hit=True,
                duration=time.time() - start_time,
                search_type="basic",
            )
            
            # Обновляем счетчики
            background_tasks.add_task(
                _update_search_metrics,
                redis_client,
                successful=True,
                cache_hit=True,
            )
            
            return cached_result
    
    # Создаем параметры поиска
    search_params = VacancySearchParams(text=request.query)
    
    if request.filters:
        for key, value in request.filters.items():
            if hasattr(search_params, key):
                setattr(search_params, key, value)
    
    # Ищем вакансии
    try:
        search_response = await hh_client.search_vacancies(
            params=search_params,
            limit=request.limit,
        )
        
        # Формируем ответ
        response = SemanticSearchResponse(
            query=request.query,
            total_results=search_response.found,
            returned_results=len(search_response.vacancies),
            vacancies=search_response.vacancies,
            search_params=search_params.dict(),
            cache_hit=False,
            processing_time=(time.time() - start_time) * 1000,
        )
        
        # Сохраняем в кэш
        if redis_client.enabled and not cache_hit:
            await redis_client.cache_search_result(
                query=request.query,
                filters=request.filters,
                result=response,
            )
        
        # Логируем запрос
        log_search_query(
            query=request.query,
            results_count=len(search_response.vacancies),
            cache_hit=False,
            duration=time.time() - start_time,
            search_type="basic",
        )
        
        # Обновляем счетчики
        background_tasks.add_task(
            _update_search_metrics,
            redis_client,
            successful=True,
            cache_hit=False,
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Ошибка базового поиска: {e}")
        
        # Обновляем счетчики ошибок
        background_tasks.add_task(
            _update_search_metrics,
            redis_client,
            successful=False,
            cache_hit=False,
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка поиска: {str(e)}"
        )


@router.get("/search/similar/{vacancy_id}")
async def find_similar_vacancies(
    vacancy_id: str,
    top_k: int = 10,
    hh_client: HHClient = Depends(get_hh_client),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> Dict[str, Any]:
    """
    Находит вакансии, похожие на указанную.
    
    Параметры:
    - vacancy_id: ID вакансии в HH.ru
    - top_k: Количество похожих вакансий для возврата
    
    Возвращает:
    - Референсную вакансию
    - Список похожих вакансий с scores сходства
    """
    try:
        # Получаем reference вакансию
        reference_vacancy = await hh_client.get_vacancy_by_id(vacancy_id)
        
        if not reference_vacancy:
            raise HTTPException(
                status_code=404,
                detail=f"Вакансия с ID {vacancy_id} не найдена"
            )
        
        # Ищем похожие вакансии по профессии и локации
        search_params = VacancySearchParams(
            text=reference_vacancy.name,
            area=reference_vacancy.area_id,
        )
        
        search_response = await hh_client.search_vacancies(
            params=search_params,
            limit=top_k * 3,  # Ищем больше, чтобы после фильтрации осталось достаточно
        )
        
        if not search_response.vacancies:
            return {
                "reference_vacancy": reference_vacancy,
                "similar_vacancies": [],
                "message": "Похожих вакансий не найдено",
            }
        
        # Исключаем reference вакансию из результатов
        other_vacancies = [
            v for v in search_response.vacancies 
            if v.id != vacancy_id
        ]
        
        # Находим похожие с помощью эмбеддингов
        similar_vacancies = await embedding_service.find_similar_vacancies(
            reference_vacancy=reference_vacancy,
            vacancies=other_vacancies,
            top_k=top_k,
        )
        
        return {
            "reference_vacancy": reference_vacancy,
            "similar_vacancies": [
                {
                    "vacancy": vacancy,
                    "similarity_score": score,
                }
                for vacancy, score in similar_vacancies
            ],
            "total_found": len(similar_vacancies),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка поиска похожих вакансий: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка поиска похожих вакансий: {str(e)}"
        )


async def _update_search_metrics(
    redis_client: RedisCache,
    successful: bool,
    cache_hit: bool,
):
    """
    Обновляет счетчики метрик поиска в фоне.
    
    Args:
        redis_client: Redis клиент
        successful: Успешный ли поиск
        cache_hit: Попадание в кэш
    """
    if not redis_client.enabled:
        return
    
    try:
        # Инкрементируем общий счетчик запросов
        await redis_client.increment_counter("metrics:search_requests")
        
        if successful:
            await redis_client.increment_counter("metrics:successful_searches")
        else:
            await redis_client.increment_counter("metrics:failed_searches")
        
        if cache_hit:
            await redis_client.increment_counter("metrics:cache_hits")
        else:
            await redis_client.increment_counter("metrics:cache_misses")
            
    except Exception as e:
        logger.error(f"Ошибка обновления метрик поиска: {e}")