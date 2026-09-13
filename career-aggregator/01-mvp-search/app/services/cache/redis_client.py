"""
Клиент Redis для кэширования данных.

Этот модуль предоставляет асинхронный клиент Redis для кэширования
результатов поиска, эмбеддингов и других данных.
"""

import json
import hashlib
import pickle
from typing import Any, Optional, Dict, List, Union
from datetime import timedelta
import redis.asyncio as redis
from loguru import logger

from app.core.config import settings
from app.core.logging import log_function_call
from app.models.hh import CacheStats


class CacheError(Exception):
    """Базовое исключение для ошибок кэширования."""
    pass


class RedisCache:
    """
    Асинхронный клиент Redis для кэширования.
    
    Обеспечивает:
    - Кэширование результатов поиска вакансий
    - Кэширование эмбеддингов
    - Кэширование распарсенных запросов
    - Статистику использования кэша
    - TTL управление
    """
    
    def __init__(self):
        """Инициализирует Redis клиент."""
        self.redis_url = settings.redis_url
        self.ttl = settings.redis_cache_ttl
        self.max_entries = settings.redis_max_entries
        self.enabled = settings.cache_enabled
        
        self.client: Optional[redis.Redis] = None
        
        logger.info(
            f"Инициализация Redis кэша. "
            f"URL: {self.redis_url}, TTL: {self.ttl} сек, "
            f"Включен: {self.enabled}"
        )
    
    async def connect(self):
        """
        Устанавливает подключение к Redis.
        
        Raises:
            CacheError: При ошибке подключения
        """
        if not self.enabled:
            logger.warning("Кэширование отключено в настройках")
            return
        
        try:
            self.client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,  # Для бинарных данных
            )
            
            # Проверяем подключение
            await self.client.ping()
            
            logger.info(f"Подключение к Redis установлено: {self.redis_url}")
            
        except Exception as e:
            logger.error(f"Ошибка подключения к Redis: {e}")
            self.enabled = False
            raise CacheError(f"Не удалось подключиться к Redis: {e}")
    
    async def close(self):
        """Закрывает подключение к Redis."""
        if self.client:
            await self.client.close()
            self.client = None
            logger.debug("Подключение к Redis закрыто")
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Генерирует ключ для кэша на основе аргументов.
        
        Args:
            prefix: Префикс ключа
            *args: Позиционные аргументы
            **kwargs: Именованные аргументы
        
        Returns:
            Строковый ключ для кэша
        """
        # Создаем строковое представление аргументов
        key_parts = [prefix]
        
        for arg in args:
            key_parts.append(str(arg))
        
        for key, value in sorted(kwargs.items()):
            key_parts.append(f"{key}:{value}")
        
        key_string = ":".join(key_parts)
        
        # Хэшируем если ключ слишком длинный
        if len(key_string) > 100:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            return f"{prefix}:{key_hash}"
        
        return key_string
    
    @log_function_call
    async def get(self, key: str) -> Optional[Any]:
        """
        Получает значение из кэша по ключу.
        
        Args:
            key: Ключ кэша
        
        Returns:
            Значение из кэша или None если не найдено
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            data = await self.client.get(key)
            
            if data is None:
                return None
            
            # Десериализуем данные
            try:
                return pickle.loads(data)
            except (pickle.PickleError, TypeError):
                # Пробуем JSON десериализацию
                try:
                    return json.loads(data.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError) as decode_error:
                    logger.warning(
                        f"Не удалось десериализовать данные для ключа: {key}. "
                        f"Ошибка: {type(decode_error).__name__}"
                    )
                    return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении из кэша (ключ: {key}): {e}")
            return None
    
    @log_function_call
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Сохраняет значение в кэш.
        
        Args:
            key: Ключ кэша
            value: Значение для сохранения
            ttl: Время жизни в секундах (None = использовать настройки)
        
        Returns:
            True если успешно, False в противном случае
        """
        if not self.enabled or not self.client:
            return False
        
        if ttl is None:
            ttl = self.ttl
        
        try:
            # Сериализуем данные
            try:
                # Пробуем pickle для сложных объектов
                data = pickle.dumps(value)
            except (pickle.PickleError, TypeError):
                # Пробуем JSON для простых объектов
                try:
                    data = json.dumps(value).encode('utf-8')
                except (TypeError, ValueError):
                    logger.warning(f"Не удалось сериализовать данные для ключа: {key}")
                    return False
            
            # Сохраняем в Redis
            if ttl > 0:
                await self.client.setex(key, ttl, data)
            else:
                await self.client.set(key, data)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении в кэш (ключ: {key}): {e}")
            return False
    
    @log_function_call
    async def delete(self, key: str) -> bool:
        """
        Удаляет значение из кэша.
        
        Args:
            key: Ключ кэша
        
        Returns:
            True если успешно, False в противном случае
        """
        if not self.enabled or not self.client:
            return False
        
        try:
            result = await self.client.delete(key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Ошибка при удалении из кэша (ключ: {key}): {e}")
            return False
    
    @log_function_call
    async def clear(self, pattern: str = "*") -> int:
        """
        Очищает кэш по паттерну.
        
        Args:
            pattern: Паттерн ключей для удаления
        
        Returns:
            Количество удаленных ключей
        """
        if not self.enabled or not self.client:
            return 0
        
        try:
            keys = await self.client.keys(pattern)
            if keys:
                await self.client.delete(*keys)
            
            logger.info(f"Очистка кэша. Удалено ключей: {len(keys)}")
            return len(keys)
            
        except Exception as e:
            logger.error(f"Ошибка при очистке кэша: {e}")
            return 0
    
    @log_function_call
    async def get_stats(self) -> CacheStats:
        """
        Возвращает статистику кэша.
        
        Returns:
            Статистика использования кэша
        """
        if not self.enabled or not self.client:
            return CacheStats()
        
        try:
            info = await self.client.info("stats")
            
            hits = int(info.get("keyspace_hits", 0))
            misses = int(info.get("keyspace_misses", 0))
            total = hits + misses
            
            hit_rate = hits / total if total > 0 else 0.0
            
            # Получаем информацию о памяти
            memory_info = await self.client.info("memory")
            used_memory = int(memory_info.get("used_memory", 0))
            
            # Получаем количество ключей
            db_info = await self.client.info("keyspace")
            total_keys = 0
            for db_data in db_info.values():
                if isinstance(db_data, dict):
                    total_keys += int(db_data.get("keys", 0))
            
            # Получаем средний TTL (упрощенно)
            avg_ttl = 0.0
            try:
                # Берем случайные ключи для оценки
                random_keys = await self.client.randomkey(count=min(100, total_keys))
                if random_keys:
                    ttls = []
                    for key in random_keys:
                        ttl = await self.client.ttl(key)
                        if ttl > 0:
                            ttls.append(ttl)
                    if ttls:
                        avg_ttl = sum(ttls) / len(ttls)
            except Exception:
                avg_ttl = self.ttl
            
            return CacheStats(
                hits=hits,
                misses=misses,
                total=total,
                hit_rate=hit_rate,
                size=used_memory,
                avg_ttl=avg_ttl,
            )
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики кэша: {e}")
            return CacheStats()
    
    # Специализированные методы для кэширования поиска
    
    @log_function_call
    async def cache_search_result(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        result: Any = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Кэширует результат поиска.
        
        Args:
            query: Поисковый запрос
            filters: Фильтры поиска
            result: Результат поиска
            ttl: Время жизни в секундах
        
        Returns:
            True если успешно
        """
        key = self._generate_key("search", query=query, filters=filters)
        return await self.set(key, result, ttl)
    
    @log_function_call
    async def get_search_result(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Optional[Any]:
        """
        Получает результат поиска из кэша.
        
        Args:
            query: Поисковый запрос
            filters: Фильтры поиска
        
        Returns:
            Результат поиска или None
        """
        key = self._generate_key("search", query=query, filters=filters)
        return await self.get(key)
    
    @log_function_call
    async def cache_embedding(
        self,
        text: str,
        embedding: List[float],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Кэширует эмбеддинг текста.
        
        Args:
            text: Исходный текст
            embedding: Векторное представление
            ttl: Время жизни в секундах
        
        Returns:
            True если успешно
        """
        key = self._generate_key("embedding", text=text)
        return await self.set(key, embedding, ttl)
    
    @log_function_call
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Получает эмбеддинг текста из кэша.
        
        Args:
            text: Исходный текст
        
        Returns:
            Эмбеддинг или None
        """
        key = self._generate_key("embedding", text=text)
        result = await self.get(key)
        
        if result is not None and isinstance(result, list):
            return result
        
        return None
    
    @log_function_call
    async def cache_parsed_query(
        self,
        query: str,
        parsed_query: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Кэширует распарсенный запрос.
        
        Args:
            query: Исходный запрос
            parsed_query: Распарсенный запрос
            ttl: Время жизни в секундах
        
        Returns:
            True если успешно
        """
        key = self._generate_key("parsed_query", query=query)
        return await self.set(key, parsed_query, ttl)
    
    @log_function_call
    async def get_parsed_query(self, query: str) -> Optional[Any]:
        """
        Получает распарсенный запрос из кэша.
        
        Args:
            query: Исходный запрос
        
        Returns:
            Распарсенный запрос или None
        """
        key = self._generate_key("parsed_query", query=query)
        return await self.get(key)
    
    @log_function_call
    async def increment_counter(self, key: str, amount: int = 1) -> int:
        """
        Инкрементирует счетчик в кэше.
        
        Args:
            key: Ключ счетчика
            amount: Значение инкремента
        
        Returns:
            Новое значение счетчика
        """
        if not self.enabled or not self.client:
            return 0
        
        try:
            return await self.client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Ошибка при инкременте счетчика {key}: {e}")
            return 0
    
    @log_function_call
    async def get_counter(self, key: str) -> int:
        """
        Получает значение счетчика из кэша.
        
        Args:
            key: Ключ счетчика
        
        Returns:
            Значение счетчика
        """
        if not self.enabled or not self.client:
            return 0
        
        try:
            value = await self.client.get(key)
            return int(value) if value else 0
        except Exception as e:
            logger.error(f"Ошибка при получении счетчика {key}: {e}")
            return 0


# Глобальный экземпляр кэша
_redis_cache: Optional[RedisCache] = None


async def get_redis_client() -> RedisCache:
    """
    Возвращает экземпляр Redis клиента.
    
    Используется для dependency injection.
    """
    global _redis_cache
    
    if _redis_cache is None:
        _redis_cache = RedisCache()
        if _redis_cache.enabled:
            await _redis_cache.connect()
    
    return _redis_cache


async def close_redis_client():
    """Закрывает подключение Redis."""
    global _redis_cache
    if _redis_cache:
        await _redis_cache.close()
        _redis_cache = None