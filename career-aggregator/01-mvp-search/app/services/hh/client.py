"""
Клиент для работы с HH.ru API.

Этот модуль предоставляет асинхронный клиент для взаимодействия
с API HH.ru, включая поиск вакансий и получение справочных данных.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from urllib.parse import urlencode
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from loguru import logger

from app.core.config import settings
from app.core.logging import log_function_call
from app.models.hh import (
    Vacancy,
    VacancySearchParams,
    VacancySearchResponse,
    Area,
    Specialization,
    Industry,
    Schedule,
    ExperienceLevel,
)


class HHClientError(Exception):
    """Базовое исключение для ошибок HH.ru клиента."""
    pass


class HHAPIRateLimitError(HHClientError):
    """Исключение при превышении rate limit HH.ru API."""
    pass


class HHAPIAuthError(HHClientError):
    """Исключение при ошибках аутентификации."""
    pass


class HHAPINotFoundError(HHClientError):
    """Исключение при 404 ошибках."""
    pass


class HHClient:
    """
    Асинхронный клиент для HH.ru API.
    
    Обеспечивает:
    - Поиск вакансий с пагинацией
    - Получение справочных данных (регионы, специализации и т.д.)
    - Обработку ошибок и retry логику
    - Rate limiting
    """
    
    def __init__(self):
        """Инициализирует клиент HH.ru API."""
        self.base_url = str(settings.hh_api_base_url)
        self.user_agent = settings.hh_user_agent
        self.request_delay = settings.request_delay
        self.max_vacancies = settings.hh_max_vacancies_per_request
        self.page_size = settings.hh_page_size
        self.max_pages = settings.hh_max_pages
        
        # HTTP клиент с настройками
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
                "HH-User-Agent": self.user_agent,
            },
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
        )
        
        logger.info(f"HH.ru клиент инициализирован. Base URL: {self.base_url}")
    
    async def close(self):
        """Закрывает HTTP клиент."""
        await self.client.aclose()
        logger.debug("HH.ru клиент закрыт")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, HHAPIRateLimitError)),
        reraise=True,
    )
    @log_function_call
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Выполняет HTTP запрос к HH.ru API.
        
        Args:
            method: HTTP метод (GET, POST, etc.)
            endpoint: Конечная точка API
            params: Параметры запроса
            data: Тело запроса (для POST)
        
        Returns:
            Ответ API в виде словаря
        
        Raises:
            HHAPIRateLimitError: При превышении rate limit
            HHAPIAuthError: При ошибках аутентификации
            HHAPINotFoundError: При 404 ошибках
            HHClientError: При других ошибках API
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                params=params,
                json=data,
            )
            
            # Обработка статус кодов
            if response.status_code == 200:
                return response.json()
            
            elif response.status_code == 429:
                logger.warning(f"Rate limit превышен для {endpoint}")
                raise HHAPIRateLimitError("Превышен rate limit HH.ru API")
            
            elif response.status_code == 403:
                logger.error(f"Доступ запрещен для {endpoint}")
                raise HHAPIAuthError("Доступ к HH.ru API запрещен")
            
            elif response.status_code == 404:
                logger.warning(f"Ресурс не найден: {endpoint}")
                raise HHAPINotFoundError(f"Ресурс не найден: {endpoint}")
            
            elif response.status_code >= 500:
                logger.error(f"Ошибка сервера HH.ru: {response.status_code}")
                response.raise_for_status()
            
            else:
                logger.error(f"Неожиданный статус код: {response.status_code}")
                response.raise_for_status()
                
        except httpx.RequestError as e:
            logger.error(f"Ошибка сети при запросе к HH.ru API: {e}")
            raise HHClientError(f"Ошибка сети: {e}")
        
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON ответа HH.ru: {e}")
            raise HHClientError(f"Ошибка парсинга JSON: {e}")
    
    @log_function_call
    async def search_vacancies(
        self,
        params: VacancySearchParams,
        limit: Optional[int] = None,
    ) -> VacancySearchResponse:
        """
        Ищет вакансии по заданным параметрам.
        
        Args:
            params: Параметры поиска вакансий
            limit: Максимальное количество вакансий для возврата
        
        Returns:
            Ответ с найденными вакансиями и метаданными
        """
        logger.info(f"Поиск вакансий с параметрами: {params.dict(exclude_none=True)}")
        
        # Преобразуем параметры в формат HH.ru API
        api_params = self._convert_search_params(params)
        
        # Если указан limit, вычисляем необходимое количество страниц
        if limit and limit > 0:
            pages_needed = min(
                (limit + self.page_size - 1) // self.page_size,
                self.max_pages
            )
        else:
            pages_needed = self.max_pages
        
        vacancies = []
        total_found = 0
        pages_processed = 0
        
        # Обрабатываем страницы с пагинацией
        for page in range(pages_needed):
            api_params["page"] = page
            api_params["per_page"] = self.page_size
            
            try:
                # Задержка между запросами для соблюдения rate limit
                if page > 0:
                    await asyncio.sleep(self.request_delay)
                
                data = await self._make_request("GET", "/vacancies", params=api_params)
                
                # Сохраняем общее количество найденных вакансий
                if page == 0:
                    total_found = data.get("found", 0)
                    logger.info(f"Найдено вакансий: {total_found}")
                
                # Преобразуем вакансии из API в наши модели
                page_vacancies = [
                    self._parse_vacancy_item(item)
                    for item in data.get("items", [])
                ]
                
                vacancies.extend(page_vacancies)
                pages_processed += 1
                
                # Логируем прогресс
                logger.debug(
                    f"Обработана страница {page + 1}. "
                    f"Вакансий на странице: {len(page_vacancies)}. "
                    f"Всего собрано: {len(vacancies)}"
                )
                
                # Проверяем, достаточно ли вакансий собрали
                if limit and len(vacancies) >= limit:
                    vacancies = vacancies[:limit]
                    break
                
                # Проверяем, есть ли еще страницы
                if page >= data.get("pages", 1) - 1:
                    break
                    
            except Exception as e:
                logger.error(f"Ошибка при обработке страницы {page}: {e}")
                # Продолжаем со следующей страницей, если это не критическая ошибка
                if isinstance(e, (HHAPIAuthError, HHAPIRateLimitError)):
                    raise
                continue
        
        logger.info(
            f"Поиск завершен. Обработано страниц: {pages_processed}. "
            f"Найдено вакансий: {len(vacancies)}"
        )
        
        return VacancySearchResponse(
            found=total_found,
            vacancies=vacancies,
            search_params=params,
            pages_processed=pages_processed,
        )
    
    @log_function_call
    async def get_vacancy_by_id(self, vacancy_id: str) -> Optional[Vacancy]:
        """
        Получает детальную информацию о вакансии по ID.
        
        Args:
            vacancy_id: ID вакансии в HH.ru
        
        Returns:
            Детальная информация о вакансии или None если не найдена
        """
        try:
            data = await self._make_request("GET", f"/vacancies/{vacancy_id}")
            return self._parse_vacancy_detail(data)
        except HHAPINotFoundError:
            logger.warning(f"Вакансия {vacancy_id} не найдена")
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении вакансии {vacancy_id}: {e}")
            return None
    
    @log_function_call
    async def get_areas(self) -> List[Area]:
        """
        Получает список регионов/городов.
        
        Returns:
            Список регионов с иерархической структурой
        """
        try:
            data = await self._make_request("GET", "/areas")
            return self._parse_areas(data)
        except Exception as e:
            logger.error(f"Ошибка при получении регионов: {e}")
            return []
    
    @log_function_call
    async def get_specializations(self) -> List[Specialization]:
        """
        Получает список специализаций (профессий).
        
        Returns:
            Список специализаций с иерархической структурой
        """
        try:
            data = await self._make_request("GET", "/specializations")
            return self._parse_specializations(data)
        except Exception as e:
            logger.error(f"Ошибка при получении специализаций: {e}")
            return []
    
    @log_function_call
    async def get_industries(self) -> List[Industry]:
        """
        Получает список отраслей.
        
        Returns:
            Список отраслей
        """
        try:
            data = await self._make_request("GET", "/industries")
            return self._parse_industries(data)
        except Exception as e:
            logger.error(f"Ошибка при получении отраслей: {e}")
            return []
    
    @log_function_call
    async def get_schedules(self) -> List[Schedule]:
        """
        Получает список графиков работы.
        
        Returns:
            Список графиков работы
        """
        try:
            data = await self._make_request("GET", "/schedules")
            return self._parse_schedules(data)
        except Exception as e:
            logger.error(f"Ошибка при получении графиков работы: {e}")
            return []
    
    @log_function_call
    async def get_experience_levels(self) -> List[ExperienceLevel]:
        """
        Получает список уровней опыта.
        
        Returns:
            Список уровней опыта
        """
        try:
            # Note: HH.ru не имеет отдельного endpoint для уровней опыта
            # Используем статический список на основе документации
            return [
                ExperienceLevel(id="noExperience", name="Нет опыта"),
                ExperienceLevel(id="between1And3", name="От 1 года до 3 лет"),
                ExperienceLevel(id="between3And6", name="От 3 до 6 лет"),
                ExperienceLevel(id="moreThan6", name="Более 6 лет"),
            ]
        except Exception as e:
            logger.error(f"Ошибка при получении уровней опыта: {e}")
            return []
    
    def _convert_search_params(self, params: VacancySearchParams) -> Dict[str, Any]:
        """
        Преобразует параметры поиска в формат HH.ru API.
        
        Args:
            params: Параметры поиска в нашем формате
        
        Returns:
            Параметры в формате HH.ru API
        """
        api_params = {}
        
        # Текстовый поиск
        if params.text:
            api_params["text"] = params.text
        
        # Регион
        if params.area:
            api_params["area"] = params.area
        
        # Специализация
        if params.specialization:
            api_params["specialization"] = params.specialization
        
        # Опыт
        if params.experience:
            api_params["experience"] = params.experience
        
        # График работы
        if params.schedule:
            api_params["schedule"] = params.schedule
        
        # Тип занятости
        if params.employment:
            api_params["employment"] = params.employment
        
        # Зарплата
        if params.salary:
            api_params["salary"] = params.salary
        
        if params.currency:
            api_params["currency"] = params.currency
        
        # Сортировка
        if params.order_by:
            api_params["order_by"] = params.order_by
        
        # Дата публикации
        if params.date_from:
            api_params["date_from"] = params.date_from.isoformat()
        
        # Дополнительные параметры
        api_params["only_with_salary"] = params.only_with_salary
        api_params["per_page"] = self.page_size
        
        return {k: v for k, v in api_params.items() if v is not None}
    
    def _parse_vacancy_item(self, item: Dict[str, Any]) -> Vacancy:
        """
        Парсит элемент вакансии из списка результатов.
        
        Args:
            item: Элемент вакансии из API ответа
        
        Returns:
            Объект Vacancy
        """
        # Извлекаем данные о зарплате
        salary = None
        if item.get("salary"):
            salary_data = item["salary"]
            salary = {
                "from": salary_data.get("from"),
                "to": salary_data.get("to"),
                "currency": salary_data.get("currency"),
                "gross": salary_data.get("gross"),
            }
        
        # Извлекаем ключевые навыки
        key_skills = []
        if item.get("key_skills"):
            key_skills = [skill["name"] for skill in item["key_skills"]]
        
        # Извлекаем сниппеты
        snippet = item.get("snippet", {})
        
        return Vacancy(
            id=item.get("id", ""),
            name=item.get("name", ""),
            employer=item.get("employer", {}).get("name", ""),
            employer_url=item.get("employer", {}).get("url"),
            salary=salary,
            area=item.get("area", {}).get("name", ""),
            area_id=item.get("area", {}).get("id"),
            schedule=item.get("schedule", {}).get("name", ""),
            experience=item.get("experience", {}).get("name", ""),
            description=snippet.get("requirement", "") + " " + snippet.get("responsibility", ""),
            key_skills=key_skills,
            published_at=item.get("published_at"),
            alternate_url=item.get("alternate_url", ""),
            response_url=item.get("response_url"),
            archived=item.get("archived", False),
            type=item.get("type", {}).get("name", ""),
        )
    
    def _parse_vacancy_detail(self, data: Dict[str, Any]) -> Vacancy:
        """
        Парсит детальную информацию о вакансии.
        
        Args:
            data: Детальные данные вакансии из API
        
        Returns:
            Объект Vacancy с полной информацией
        """
        # Используем общий парсер для базовых полей
        vacancy = self._parse_vacancy_item(data)
        
        # Добавляем дополнительные поля из детального ответа
        vacancy.description = data.get("description", "")
        vacancy.branded_description = data.get("branded_description")
        vacancy.contacts = data.get("contacts")
        vacancy.address = data.get("address")
        vacancy.department = data.get("department")
        vacancy.test = data.get("test")
        vacancy.employer_vacancies_url = data.get("employer", {}).get("vacancies_url")
        
        return vacancy
    
    def _parse_areas(self, data: List[Dict[str, Any]]) -> List[Area]:
        """
        Парсит список регионов.
        
        Args:
            data: Данные регионов из API
        
        Returns:
            Список объектов Area
        """
        def parse_area_node(node: Dict[str, Any]) -> Area:
            """Рекурсивно парсит узел региона."""
            areas = []
            for child in node.get("areas", []):
                areas.append(parse_area_node(child))
            
            return Area(
                id=node.get("id"),
                name=node.get("name"),
                parent_id=node.get("parent_id"),
                areas=areas,
            )
        
        areas = []
        for node in data:
            areas.append(parse_area_node(node))
        
        return areas
    
    def _parse_specializations(self, data: List[Dict[str, Any]]) -> List[Specialization]:
        """
        Парсит список специализаций.
        
        Args:
            data: Данные специализаций из API
        
        Returns:
            Список объектов Specialization
        """
        def parse_spec_node(node: Dict[str, Any]) -> Specialization:
            """Рекурсивно парсит узел специализации."""
            specializations = []
            for child in node.get("specializations", []):
                specializations.append(parse_spec_node(child))
            
            return Specialization(
                id=node.get("id"),
                name=node.get("name"),
                laboring=node.get("laboring", False),
                specializations=specializations,
            )
        
        specializations = []
        for node in data:
            specializations.append(parse_spec_node(node))
        
        return specializations
    
    def _parse_industries(self, data: List[Dict[str, Any]]) -> List[Industry]:
        """
        Парсит список отраслей.
        
        Args:
            data: Данные отраслей из API
        
        Returns:
            Список объектов Industry
        """
        industries = []
        for item in data:
            industries.append(
                Industry(
                    id=item.get("id"),
                    name=item.get("name"),
                )
            )
        
        return industries
    
    def _parse_schedules(self, data: List[Dict[str, Any]]) -> List[Schedule]:
        """
        Парсит список графиков работы.
        
        Args:
            data: Данные графиков работы из API
        
        Returns:
            Список объектов Schedule
        """
        schedules = []
        for item in data:
            schedules.append(
                Schedule(
                    id=item.get("id"),
                    name=item.get("name"),
                )
            )
        
        return schedules


# Фабрика для создания клиента
async def get_hh_client() -> HHClient:
    """
    Создает и возвращает экземпляр HHClient.
    
    Используется для dependency injection в FastAPI.
    """
    client = HHClient()
    return client


# Контекстный менеджер для использования клиента
class HHClientContext:
    """
    Контекстный менеджер для работы с HHClient.
    
    Пример использования:
    ```python
    async with HHClientContext() as client:
        vacancies = await client.search_vacancies(params)
    ```
    """
    
    def __init__(self):
        self.client = None
    
    async def __aenter__(self) -> HHClient:
        self.client = HHClient()
        return self.client
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.close()
