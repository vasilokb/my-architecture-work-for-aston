"""
Настройка логирования для приложения Career Aggregator 2.

Использует loguru для структурированного логирования с поддержкой
JSON формата для продакшена и цветного вывода для разработки.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger
from app.core.config import settings


def setup_logging():
    """
    Настраивает логирование для приложения.
    
    В зависимости от режима (debug/production) настраивает:
    - Формат вывода (цветной/JSON)
    - Уровень логирования
    - Выходные потоки (консоль/файл)
    - Фильтрация логов
    """
    
    # Удаляем стандартный обработчик loguru
    logger.remove()
    
    # Определяем формат логов в зависимости от режима
    if settings.debug:
        # Цветной формат для разработки
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
    else:
        # JSON формат для продакшена
        def json_format(record: Dict[str, Any]) -> str:
            """Форматирует запись лога в JSON."""
            log_entry = {
                "timestamp": record["time"].isoformat(),
                "level": record["level"].name,
                "message": record["message"],
                "module": record["name"],
                "function": record["function"],
                "line": record["line"],
                "process": record["process"].id,
                "thread": record["thread"].id,
            }
            
            # Добавляем дополнительные поля из extra
            if record.get("extra"):
                log_entry.update(record["extra"])
            
            # Добавляем exception info если есть
            if record.get("exception"):
                log_entry["exception"] = {
                    "type": str(record["exception"].type),
                    "value": str(record["exception"].value),
                    "traceback": record["exception"].traceback,
                }
            
            return json.dumps(log_entry, ensure_ascii=False)
        
        log_format = json_format
    
    # Настройка вывода в консоль
    logger.add(
        sys.stderr,
        format=log_format,
        level=settings.log_level,
        backtrace=settings.debug,  # Показывать traceback только в debug
        diagnose=settings.debug,   # Показывать diagnose только в debug
        colorize=settings.debug,   # Цветной вывод только в debug
    )
    
    # Настройка вывода в файл (если включено)
    if settings.log_to_file:
        log_file_path = Path(settings.log_file_path)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Ротация логов: 10 MB max size, сохранять 5 файлов
        logger.add(
            str(log_file_path),
            format=log_format,
            level=settings.log_level,
            rotation="10 MB",
            retention=5,
            compression="zip",
            backtrace=settings.debug,
            diagnose=settings.debug,
        )
        
        logger.info(f"Логирование в файл настроено: {log_file_path}")
    
    # Настройка фильтрации для уменьшения шума от внешних библиотек
    def filter_noisy_logs(record: Dict[str, Any]) -> bool:
        """Фильтрует шумные логи от внешних библиотек."""
        # Список модулей для фильтрации (можно расширить)
        noisy_modules = [
            "httpx",
            "httpcore",
            "urllib3",
            "asyncio",
            "uvicorn",
            "redis",
        ]
        
        module_name = record.get("name", "")
        for noisy_module in noisy_modules:
            if module_name.startswith(noisy_module):
                # Пропускаем логи ниже WARNING от шумных модулей
                return record["level"].no >= logger.level("WARNING").no
        
        return True
    
    # Применяем фильтр (только в production)
    if not settings.debug:
        logger.add(
            sys.stderr,
            format=log_format,
            level=settings.log_level,
            filter=filter_noisy_logs,
        )
    
    logger.info(f"Логирование настроено. Уровень: {settings.log_level}, Debug: {settings.debug}")


def get_logger(name: Optional[str] = None):
    """
    Возвращает настроенный логгер.
    
    Args:
        name: Имя логгера (обычно __name__ модуля)
    
    Returns:
        Настроенный экземпляр loguru logger
    """
    return logger.bind(module=name)


# Декораторы для логирования
def log_function_call(func):
    """
    Декоратор для логирования вызовов функций.
    
    Логирует входные параметры и результат выполнения функции.
    """
    import functools
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        
        # Логируем вызов функции
        logger.debug(
            f"Вызов функции {func.__name__}",
            args=args,
            kwargs=kwargs,
        )
        
        try:
            # Выполняем функцию
            start_time = datetime.now()
            result = await func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Логируем успешное выполнение
            logger.debug(
                f"Функция {func.__name__} выполнена успешно",
                execution_time=execution_time,
                result_type=type(result).__name__,
            )
            
            return result
            
        except Exception as e:
            # Логируем исключение
            logger.error(
                f"Ошибка в функции {func.__name__}",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        
        # Логируем вызов функции
        logger.debug(
            f"Вызов функции {func.__name__}",
            args=args,
            kwargs=kwargs,
        )
        
        try:
            # Выполняем функцию
            start_time = datetime.now()
            result = func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Логируем успешное выполнение
            logger.debug(
                f"Функция {func.__name__} выполнена успешно",
                execution_time=execution_time,
                result_type=type(result).__name__,
            )
            
            return result
            
        except Exception as e:
            # Логируем исключение
            logger.error(
                f"Ошибка в функции {func.__name__}",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise
    
    # Возвращаем соответствующий wrapper
    import inspect
    if inspect.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


# Контекстный менеджер для логирования блоков кода
class LoggingContext:
    """
    Контекстный менеджер для логирования выполнения блоков кода.
    
    Пример использования:
    ```python
    with LoggingContext("processing_data", logger=logger):
        # код который нужно залогировать
        process_data()
    ```
    """
    
    def __init__(self, operation: str, logger=None, level: str = "DEBUG"):
        self.operation = operation
        self.logger = logger or get_logger(__name__)
        self.level = level
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.log(
            self.level,
            f"Начало операции: {self.operation}",
            operation=self.operation,
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        execution_time = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is None:
            self.logger.log(
                self.level,
                f"Операция завершена: {self.operation}",
                operation=self.operation,
                execution_time=execution_time,
                status="success",
            )
        else:
            self.logger.log(
                "ERROR",
                f"Ошибка в операции: {self.operation}",
                operation=self.operation,
                execution_time=execution_time,
                error=str(exc_val),
                error_type=exc_type.__name__,
                status="error",
            )


# Утилиты для структурированного логирования
def log_api_call(
    endpoint: str,
    method: str,
    status_code: int,
    duration: float,
    **extra
):
    """
    Логирует вызов API endpoint.
    
    Args:
        endpoint: Путь endpoint
        method: HTTP метод
        status_code: Код ответа
        duration: Время выполнения в секундах
        **extra: Дополнительные поля для лога
    """
    logger = get_logger("api")
    
    log_data = {
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "duration": duration,
        **extra,
    }
    
    # Определяем уровень логирования по статус коду
    if status_code >= 500:
        logger.error("Ошибка сервера в API", **log_data)
    elif status_code >= 400:
        logger.warning("Ошибка клиента в API", **log_data)
    elif status_code >= 300:
        logger.info("Редирект в API", **log_data)
    else:
        logger.debug("Успешный вызов API", **log_data)


def log_search_query(
    query: str,
    results_count: int,
    cache_hit: bool,
    duration: float,
    **extra
):
    """
    Логирует поисковый запрос.
    
    Args:
        query: Поисковый запрос
        results_count: Количество найденных результатов
        cache_hit: Попадание в кэш
        duration: Время выполнения в секундах
        **extra: Дополнительные поля для лога
    """
    logger = get_logger("search")
    
    log_data = {
        "query": query,
        "results_count": results_count,
        "cache_hit": cache_hit,
        "duration": duration,
        **extra,
    }
    
    logger.info("Поисковый запрос выполнен", **log_data)


# Инициализация логирования при импорте модуля
setup_logging()