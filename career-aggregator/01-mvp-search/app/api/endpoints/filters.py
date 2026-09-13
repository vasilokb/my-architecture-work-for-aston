"""
Endpoints для получения справочных данных и фильтров.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from app.services.hh import get_hh_client, HHClient
from app.services.cache import get_redis_client, RedisCache
from app.models.hh import Area, Specialization, Industry, Schedule, ExperienceLevel


router = APIRouter()


@router.get("/filters")
async def get_all_filters(
    hh_client: HHClient = Depends(get_hh_client),
    redis_client: RedisCache = Depends(get_redis_client),
) -> Dict[str, Any]:
    """
    Возвращает все доступные фильтры для поиска.
    
    Включает:
    - Регионы/города
    - Специализации (профессии)
    - Отрасли
    - Графики работы
    - Уровни опыта
    """
    logger.info("Запрос всех фильтров")
    
    try:
        # Пробуем получить из кэша
        cached_filters = None
        if redis_client.enabled:
            cached_filters = await redis_client.get("filters:all")
        
        if cached_filters:
            logger.info("Фильтры загружены из кэша")
            return cached_filters
        
        # Загружаем данные из HH.ru API
        areas = await hh_client.get_areas()
        specializations = await hh_client.get_specializations()
        industries = await hh_client.get_industries()
        schedules = await hh_client.get_schedules()
        experience_levels = await hh_client.get_experience_levels()
        
        # Формируем ответ
        filters_data = {
            "areas": _format_areas(areas),
            "specializations": _format_specializations(specializations),
            "industries": _format_industries(industries),
            "schedules": _format_schedules(schedules),
            "experience_levels": _format_experience_levels(experience_levels),
            "metadata": {
                "areas_count": len(areas),
                "specializations_count": len(specializations),
                "industries_count": len(industries),
                "schedules_count": len(schedules),
                "experience_levels_count": len(experience_levels),
            }
        }
        
        # Сохраняем в кэш (TTL 24 часа)
        if redis_client.enabled:
            await redis_client.set("filters:all", filters_data, ttl=86400)
            logger.info("Фильтры сохранены в кэш")
        
        return filters_data
        
    except Exception as e:
        logger.error(f"Ошибка при получении фильтров: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении фильтров: {str(e)}"
        )


@router.get("/filters/areas")
async def get_areas(
    hh_client: HHClient = Depends(get_hh_client),
    redis_client: RedisCache = Depends(get_redis_client),
) -> List[Dict[str, Any]]:
    """
    Возвращает список регионов/городов.
    
    Структура иерархическая: страны -> регионы -> города.
    """
    logger.info("Запрос регионов")
    
    try:
        # Пробуем получить из кэша
        cached_areas = None
        if redis_client.enabled:
            cached_areas = await redis_client.get("filters:areas")
        
        if cached_areas:
            return cached_areas
        
        # Загружаем из HH.ru API
        areas = await hh_client.get_areas()
        formatted_areas = _format_areas(areas)
        
        # Сохраняем в кэш (TTL 24 часа)
        if redis_client.enabled:
            await redis_client.set("filters:areas", formatted_areas, ttl=86400)
        
        return formatted_areas
        
    except Exception as e:
        logger.error(f"Ошибка при получении регионов: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении регионов: {str(e)}"
        )


@router.get("/filters/specializations")
async def get_specializations(
    hh_client: HHClient = Depends(get_hh_client),
    redis_client: RedisCache = Depends(get_redis_client),
) -> List[Dict[str, Any]]:
    """
    Возвращает список специализаций (профессий).
    
    Структура иерархическая: категории -> подкатегории -> специализации.
    """
    logger.info("Запрос специализаций")
    
    try:
        # Пробуем получить из кэша
        cached_specializations = None
        if redis_client.enabled:
            cached_specializations = await redis_client.get("filters:specializations")
        
        if cached_specializations:
            return cached_specializations
        
        # Загружаем из HH.ru API
        specializations = await hh_client.get_specializations()
        formatted_specializations = _format_specializations(specializations)
        
        # Сохраняем в кэш (TTL 24 часа)
        if redis_client.enabled:
            await redis_client.set("filters:specializations", formatted_specializations, ttl=86400)
        
        return formatted_specializations
        
    except Exception as e:
        logger.error(f"Ошибка при получении специализаций: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении специализаций: {str(e)}"
        )


@router.get("/filters/industries")
async def get_industries(
    hh_client: HHClient = Depends(get_hh_client),
    redis_client: RedisCache = Depends(get_redis_client),
) -> List[Dict[str, Any]]:
    """
    Возвращает список отраслей.
    """
    logger.info("Запрос отраслей")
    
    try:
        # Пробуем получить из кэша
        cached_industries = None
        if redis_client.enabled:
            cached_industries = await redis_client.get("filters:industries")
        
        if cached_industries:
            return cached_industries
        
        # Загружаем из HH.ru API
        industries = await hh_client.get_industries()
        formatted_industries = _format_industries(industries)
        
        # Сохраняем в кэш (TTL 24 часа)
        if redis_client.enabled:
            await redis_client.set("filters:industries", formatted_industries, ttl=86400)
        
        return formatted_industries
        
    except Exception as e:
        logger.error(f"Ошибка при получении отраслей: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении отраслей: {str(e)}"
        )


@router.get("/filters/schedules")
async def get_schedules(
    hh_client: HHClient = Depends(get_hh_client),
    redis_client: RedisCache = Depends(get_redis_client),
) -> List[Dict[str, Any]]:
    """
    Возвращает список графиков работы.
    """
    logger.info("Запрос графиков работы")
    
    try:
        # Пробуем получить из кэша
        cached_schedules = None
        if redis_client.enabled:
            cached_schedules = await redis_client.get("filters:schedules")
        
        if cached_schedules:
            return cached_schedules
        
        # Загружаем из HH.ru API
        schedules = await hh_client.get_schedules()
        formatted_schedules = _format_schedules(schedules)
        
        # Сохраняем в кэш (TTL 24 часа)
        if redis_client.enabled:
            await redis_client.set("filters:schedules", formatted_schedules, ttl=86400)
        
        return formatted_schedules
        
    except Exception as e:
        logger.error(f"Ошибка при получении графиков работы: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении графиков работы: {str(e)}"
        )


@router.get("/filters/experience")
async def get_experience_levels(
    hh_client: HHClient = Depends(get_hh_client),
    redis_client: RedisCache = Depends(get_redis_client),
) -> List[Dict[str, Any]]:
    """
    Возвращает список уровней опыта.
    """
    logger.info("Запрос уровней опыта")
    
    try:
        # Пробуем получить из кэша
        cached_experience = None
        if redis_client.enabled:
            cached_experience = await redis_client.get("filters:experience")
        
        if cached_experience:
            return cached_experience
        
        # Загружаем из HH.ru API
        experience_levels = await hh_client.get_experience_levels()
        formatted_experience = _format_experience_levels(experience_levels)
        
        # Сохраняем в кэш (TTL 24 часа)
        if redis_client.enabled:
            await redis_client.set("filters:experience", formatted_experience, ttl=86400)
        
        return formatted_experience
        
    except Exception as e:
        logger.error(f"Ошибка при получении уровней опыта: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении уровней опыта: {str(e)}"
        )


@router.get("/filters/popular")
async def get_popular_filters() -> Dict[str, Any]:
    """
    Возвращает популярные фильтры для быстрого доступа.
    
    Включает:
    - Популярные города
    - Популярные специализации
    - Популярные графики работы
    """
    logger.info("Запрос популярных фильтров")
    
    # Статические данные для популярных фильтров
    # В реальном приложении можно анализировать историю поиска
    
    popular_filters = {
        "popular_cities": [
            {"id": "1", "name": "Москва"},
            {"id": "2", "name": "Санкт-Петербург"},
            {"id": "16", "name": "Минск"},
            {"id": "159", "name": "Алматы"},
            {"id": "115", "name": "Киев"},
            {"id": "1202", "name": "Новосибирск"},
            {"id": "3", "name": "Екатеринбург"},
            {"id": "88", "name": "Казань"},
        ],
        "popular_specializations": [
            {"id": "1.221", "name": "Программист, разработчик"},
            {"id": "1.89", "name": "Аналитик"},
            {"id": "1.9", "name": "Архитектор"},
            {"id": "1.96", "name": "Тестировщик"},
            {"id": "1.100", "name": "Дизайнер"},
            {"id": "1.113", "name": "Менеджер проекта"},
            {"id": "1.114", "name": "Маркетолог"},
            {"id": "1.150", "name": "Системный администратор"},
        ],
        "popular_schedules": [
            {"id": "fullDay", "name": "Полный день"},
            {"id": "remote", "name": "Удаленная работа"},
            {"id": "flexible", "name": "Гибкий график"},
        ],
        "popular_experience_levels": [
            {"id": "noExperience", "name": "Нет опыта"},
            {"id": "between1And3", "name": "От 1 года до 3 лет"},
            {"id": "between3And6", "name": "От 3 до 6 лет"},
            {"id": "moreThan6", "name": "Более 6 лет"},
        ],
    }
    
    return popular_filters


def _format_areas(areas: List[Area]) -> List[Dict[str, Any]]:
    """Форматирует список регионов для API ответа."""
    def format_area(area: Area) -> Dict[str, Any]:
        formatted = {
            "id": area.id,
            "name": area.name,
            "parent_id": area.parent_id,
        }
        
        if area.areas:
            formatted["areas"] = [format_area(child) for child in area.areas]
        
        return formatted
    
    return [format_area(area) for area in areas]


def _format_specializations(specializations: List[Specialization]) -> List[Dict[str, Any]]:
    """Форматирует список специализаций для API ответа."""
    def format_specialization(spec: Specialization) -> Dict[str, Any]:
        formatted = {
            "id": spec.id,
            "name": spec.name,
            "laboring": spec.laboring,
        }
        
        if spec.specializations:
            formatted["specializations"] = [
                format_specialization(child) for child in spec.specializations
            ]
        
        return formatted
    
    return [format_specialization(spec) for spec in specializations]


def _format_industries(industries: List[Industry]) -> List[Dict[str, Any]]:
    """Форматирует список отраслей для API ответа."""
    return [
        {
            "id": industry.id,
            "name": industry.name,
        }
        for industry in industries
    ]


def _format_schedules(schedules: List[Schedule]) -> List[Dict[str, Any]]:
    """Форматирует список графиков работы для API ответа."""
    return [
        {
            "id": schedule.id,
            "name": schedule.name,
        }
        for schedule in schedules
    ]


def _format_experience_levels(levels: List[ExperienceLevel]) -> List[Dict[str, Any]]:
    """Форматирует список уровней опыта для API ответа."""
    return [
        {
            "id": level.id,
            "name": level.name,
        }
        for level in levels
    ]