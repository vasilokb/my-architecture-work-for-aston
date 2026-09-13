"""
Сервис для работы с LLM (DeepSeek API).

Этот модуль предоставляет функциональность для парсинга
естественно-языковых запросов с использованием LLM.
"""

import json
import asyncio
from typing import Dict, List, Optional, Any
from loguru import logger
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.core.logging import log_function_call
from app.models.hh import ParsedQuery


class LLMServiceError(Exception):
    """Базовое исключение для ошибок LLM сервиса."""
    pass


class LLMAPIError(LLMServiceError):
    """Исключение при ошибках API LLM."""
    pass


class LLMParsingError(LLMServiceError):
    """Исключение при ошибках парсинга ответа LLM."""
    pass


class LLMService:
    """
    Сервис для работы с LLM (DeepSeek API).
    
    Обеспечивает:
    - Парсинг естественно-языковых запросов о вакансиях
    - Извлечение структурированных параметров из текста
    - Fallback на rule-based парсинг при недоступности LLM
    """
    
    def __init__(self):
        """Инициализирует сервис LLM."""
        self.api_key = settings.deepseek_api_key
        self.api_url = str(settings.deepseek_api_url)
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        
        # Системный промпт для парсинга запросов
        self.system_prompt = """Ты помощник для парсинга поисковых запросов о вакансиях. 
Извлекай из запроса пользователя следующие параметры:

1. Профессия/должность (например: "системный аналитик", "python разработчик")
2. Локация (город/регион, например: "Москва", "удаленно")
3. Уровень опыта (например: "junior", "middle", "senior", "стажер")
4. Тип занятости/график (например: "полный день", "удаленная работа", "гибкий график")
5. Ключевые навыки (если упомянуты)

Если параметр не указан явно, оставляй поле пустым или null.
Возвращай ответ ТОЛЬКО в формате JSON без дополнительного текста.

Пример ответа:
{
  "profession": "системный аналитик",
  "location": "Москва",
  "experience": "middle",
  "schedule": "полный день",
  "employment": null,
  "skills": ["BPMN", "UML", "SQL"]
}"""
        
        # HTTP клиент
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(120.0, connect=15.0, read=90.0),
        )
        
        logger.info(f"LLM сервис инициализирован. Модель: {self.model}")
    
    async def close(self):
        """Закрывает HTTP клиент."""
        await self.client.aclose()
        logger.debug("LLM сервис закрыт")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, LLMAPIError)),
        reraise=True,
    )
    @log_function_call
    async def _call_llm_api(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Вызывает LLM API с заданными сообщениями.
        
        Args:
            messages: Список сообщений в формате OpenAI
        
        Returns:
            Ответ API
        
        Raises:
            LLMAPIError: При ошибках API
        """
        if not self.api_key:
            raise LLMAPIError("API ключ DeepSeek не настроен")
        
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "response_format": {"type": "json_object"},
            }
            
            response = await self.client.post(
                f"{self.api_url}/chat/completions",
                json=payload,
            )
            
            if response.status_code != 200:
                logger.error(f"Ошибка LLM API: {response.status_code} - {response.text}")
                raise LLMAPIError(f"Ошибка LLM API: {response.status_code}")
            
            data = response.json()
            
            # Извлекаем содержимое ответа
            if "choices" not in data or not data["choices"]:
                raise LLMAPIError("Пустой ответ от LLM API")
            
            content = data["choices"][0]["message"]["content"]
            
            return {
                "content": content,
                "usage": data.get("usage", {}),
                "model": data.get("model", self.model),
            }
            
        except httpx.RequestError as e:
            logger.error(f"Ошибка сети при вызове LLM API: {e}")
            raise LLMAPIError(f"Ошибка сети: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON ответа LLM: {e}")
            raise LLMAPIError(f"Ошибка парсинга JSON: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при вызове LLM API: {e}")
            raise LLMAPIError(f"Неожиданная ошибка: {e}")
    
    @log_function_call
    async def parse_query(self, query: str) -> ParsedQuery:
        """
        Парсит естественно-языковой запрос о вакансиях.
        
        Args:
            query: Поисковый запрос пользователя
        
        Returns:
            Распарсенные параметры запроса
        
        Raises:
            LLMParsingError: При ошибках парсинга
        """
        if not query or not query.strip():
            logger.warning("Пустой запрос передан для парсинга")
            return ParsedQuery(raw_query=query)
        
        logger.info(f"Парсинг запроса LLM: '{query[:50]}...'")
        
        # Если API ключ не настроен, используем rule-based парсинг
        if not self.api_key:
            logger.warning("API ключ DeepSeek не настроен, используем rule-based парсинг")
            return self._rule_based_parse(query)
        
        try:
            # Подготавливаем сообщения для LLM
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Запрос: {query}"},
            ]
            
            # Вызываем LLM API
            response = await self._call_llm_api(messages)
            content = response["content"]
            
            # Парсим JSON ответ
            try:
                parsed_data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка парсинга JSON от LLM: {e}. Ответ: {content}")
                raise LLMParsingError(f"Неверный JSON формат ответа LLM: {e}")
            
            # Создаем объект ParsedQuery
            parsed_query = ParsedQuery(
                profession=parsed_data.get("profession"),
                location=parsed_data.get("location"),
                experience=parsed_data.get("experience"),
                schedule=parsed_data.get("schedule"),
                employment=parsed_data.get("employment"),
                skills=parsed_data.get("skills", []),
                raw_query=query,
            )
            
            logger.info(
                f"Запрос успешно распарсен LLM. "
                f"Профессия: {parsed_query.profession}, "
                f"Локация: {parsed_query.location}, "
                f"Опыт: {parsed_query.experience}"
            )
            
            return parsed_query
            
        except (LLMAPIError, LLMParsingError):
            # При ошибках LLM используем rule-based парсинг как fallback
            logger.warning("Ошибка LLM парсинга, используем rule-based fallback")
            return self._rule_based_parse(query)
        except Exception as e:
            logger.error(f"Неожиданная ошибка при парсинге запроса: {e}")
            raise LLMParsingError(f"Неожиданная ошибка парсинга: {e}")
    
    def _rule_based_parse(self, query: str) -> ParsedQuery:
        """
        Rule-based парсинг запроса (fallback когда LLM недоступен).
        
        Args:
            query: Поисковый запрос пользователя
        
        Returns:
            Распарсенные параметры запроса
        """
        logger.info(f"Rule-based парсинг запроса: '{query}'")
        
        query_lower = query.lower()
        
        # Извлекаем профессию (первое существительное или словосочетание)
        profession = None
        profession_keywords = [
            "разработчик", "аналитик", "тестировщик", "дизайнер", "менеджер",
            "инженер", "архитектор", "администратор", "специалист", "консультант",
            "программист", "devops", "data scientist", "машинное обучение",
            "системный администратор", "сетевой инженер", "базы данных",
        ]
        
        for keyword in profession_keywords:
            if keyword in query_lower:
                # Находим контекст вокруг ключевого слова
                profession = self._extract_profession_context(query, keyword)
                break
        
        # Извлекаем локацию
        location = None
        location_keywords = [
            "москва", "санкт-петербург", "спб", "минск", "киев", "алматы",
            "новосибирск", "екатеринбург", "казань", "нижний новгород",
            "удаленно", "удаленная работа", "remote", "офис", "гибрид",
        ]
        
        for keyword in location_keywords:
            if keyword in query_lower:
                location = keyword
                break
        
        # Извлекаем опыт
        experience = None
        experience_patterns = [
            ("стажер", "нет опыта"),
            ("junior", "нет опыта"),
            ("начальный уровень", "нет опыта"),
            ("1-3 года", "1-3 года"),
            ("1-3 лет", "1-3 года"),
            ("middle", "1-3 года"),
            ("3-6 лет", "3-6 лет"),
            ("3-6 года", "3-6 лет"),
            ("senior", "3-6 лет"),
            ("сеньор", "3-6 лет"),
            ("более 6 лет", "более 6 лет"),
            ("lead", "более 6 лет"),
            ("руководитель", "более 6 лет"),
        ]
        
        for pattern, exp in experience_patterns:
            if pattern in query_lower:
                experience = exp
                break
        
        # Извлекаем график работы
        schedule = None
        schedule_patterns = [
            ("полный день", "полный день"),
            ("удаленная работа", "удаленная работа"),
            ("удаленка", "удаленная работа"),
            ("гибкий график", "гибкий график"),
            ("сменный график", "сменный график"),
            ("вахтовый метод", "вахтовый метод"),
        ]
        
        for pattern, sched in schedule_patterns:
            if pattern in query_lower:
                schedule = sched
                break
        
        # Извлекаем навыки (упрощенно)
        skills = []
        skill_keywords = [
            "python", "java", "javascript", "typescript", "react", "angular",
            "vue", "node.js", "docker", "kubernetes", "aws", "azure", "gcp",
            "sql", "nosql", "postgresql", "mongodb", "redis", "kafka",
            "git", "ci/cd", "jenkins", "terraform", "ansible", "linux",
            "машинное обучение", "нейросети", "ai", "computer vision",
        ]
        
        for skill in skill_keywords:
            if skill in query_lower:
                skills.append(skill)
        
        parsed_query = ParsedQuery(
            profession=profession,
            location=location,
            experience=experience,
            schedule=schedule,
            employment=None,
            skills=skills,
            raw_query=query,
        )
        
        logger.info(
            f"Rule-based парсинг завершен. "
            f"Профессия: {profession}, Локация: {location}, Опыт: {experience}"
        )
        
        return parsed_query
    
    def _extract_profession_context(self, query: str, keyword: str) -> str:
        """
        Извлекает контекст профессии вокруг ключевого слова.
        
        Args:
            query: Исходный запрос
            keyword: Найденное ключевое слово
        
        Returns:
            Контекст профессии
        """
        query_lower = query.lower()
        keyword_index = query_lower.find(keyword)
        
        if keyword_index == -1:
            return keyword
        
        # Ищем начало фразы (предыдущие 2-3 слова)
        start = max(0, keyword_index - 30)
        context_start = query_lower.rfind(' ', start, keyword_index)
        if context_start == -1:
            context_start = start
        
        # Ищем конец фразы (следующие 2-3 слова)
        end = min(len(query_lower), keyword_index + len(keyword) + 30)
        context_end = query_lower.find(' ', keyword_index + len(keyword), end)
        if context_end == -1:
            context_end = end
        
        # Извлекаем и капитализируем первую букву
        profession = query[context_start:context_end].strip()
        if profession:
            profession = profession[0].upper() + profession[1:]
        
        return profession if profession else keyword
    
    @log_function_call
    async def batch_parse_queries(self, queries: List[str]) -> List[ParsedQuery]:
        """
        Парсит несколько запросов батчем.
        
        Args:
            queries: Список поисковых запросов
        
        Returns:
            Список распарсенных запросов
        """
        if not queries:
            return []
        
        logger.info(f"Пакетный парсинг {len(queries)} запросов")
        
        # Парсим каждый запрос параллельно
        tasks = [self.parse_query(query) for query in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем результаты
        parsed_queries = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Ошибка при парсинге запроса '{queries[i][:30]}...': {result}")
                # Используем rule-based парсинг как fallback
                parsed_queries.append(self._rule_based_parse(queries[i]))
            else:
                parsed_queries.append(result)
        
        logger.info(f"Пакетный парсинг завершен. Успешно: {len(parsed_queries)}/{len(queries)}")
        
        return parsed_queries


# Фабрика для создания сервиса
async def get_llm_service() -> LLMService:
    """
    Возвращает экземпляр LLM сервиса.
    
    Используется для dependency injection.
    """
    service = LLMService()
    return service