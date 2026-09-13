"""
Конфигурация приложения Career Aggregator 2.

Этот модуль содержит настройки приложения, загружаемые из переменных окружения
и валидируемые с помощью Pydantic.
"""

import os
from typing import Optional, List
from pydantic import Field, validator
from pydantic.networks import HttpUrl
from pydantic_settings import BaseSettings
from loguru import logger


class Settings(BaseSettings):
    """Основные настройки приложения."""
    
    # ============================================
    # Общие настройки
    # ============================================
    app_name: str = "Career Aggregator 2"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # ============================================
    # HH.ru API Configuration
    # ============================================
    hh_api_base_url: HttpUrl = Field(
        default="https://api.hh.ru",
        env="HH_API_BASE_URL"
    )
    hh_user_agent: str = Field(
        default="CareerAggregator/1.0 (anonymous@example.com)",
        env="HH_USER_AGENT"
    )
    hh_api_token: Optional[str] = Field(default=None, env="HH_API_TOKEN")
    
    # Ограничения HH.ru API
    hh_max_vacancies_per_request: int = Field(
        default=2000,
        env="MAX_VACANCIES_PER_REQUEST"
    )
    hh_page_size: int = Field(default=100, env="HH_PAGE_SIZE")
    hh_max_pages: int = Field(default=20, env="HH_MAX_PAGES")
    
    # ============================================
    # LLM Service Configuration (DeepSeek)
    # ============================================
    deepseek_api_key: Optional[str] = Field(default=None, env="DEEPSEEK_API_KEY")
    deepseek_api_url: HttpUrl = Field(
        default="https://api.deepseek.com",
        env="DEEPSEEK_API_URL"
    )
    llm_model: str = Field(default="deepseek-chat", env="LLM_MODEL")
    llm_temperature: float = Field(default=0.1, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=500, env="LLM_MAX_TOKENS")
    
    # ============================================
    # Embedding Service Configuration
    # ============================================
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        env="EMBEDDING_MODEL"
    )
    embedding_device: str = Field(default="cpu", env="EMBEDDING_DEVICE")
    embedding_dimension: int = Field(default=384, env="EMBEDDING_DIMENSION")
    embedding_normalize: bool = Field(default=True, env="EMBEDDING_NORMALIZE")
    embedding_cache_dir: str = Field(
        default="./models_cache",
        env="EMBEDDING_CACHE_DIR"
    )
    
    # ============================================
    # Redis Cache Configuration
    # ============================================
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_cache_ttl: int = Field(default=3600, env="REDIS_CACHE_TTL")
    redis_max_entries: int = Field(default=1000, env="REDIS_MAX_ENTRIES")
    
    # ============================================
    # FastAPI Backend Configuration
    # ============================================
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_workers: int = Field(default=4, env="API_WORKERS")
    
    # CORS настройки
    cors_origins: List[str] = Field(
        default=["http://localhost:8501", "http://127.0.0.1:8501"],
        env="CORS_ORIGINS"
    )
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Парсит строку с CORS origins в список."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # ============================================
    # Streamlit UI Configuration
    # ============================================
    streamlit_host: str = Field(default="0.0.0.0", env="STREAMLIT_HOST")
    streamlit_port: int = Field(default=8501, env="STREAMLIT_PORT")
    streamlit_theme: str = Field(default="light", env="STREAMLIT_THEME")
    
    # ============================================
    # Search Configuration
    # ============================================
    relevance_threshold: float = Field(default=0.3, env="RELEVANCE_THRESHOLD")
    max_results_to_return: int = Field(default=50, env="MAX_RESULTS_TO_RETURN")
    cache_enabled: bool = Field(default=True, env="CACHE_ENABLED")
    
    # ============================================
    # Development & Debugging
    # ============================================
    mock_mode: bool = Field(default=False, env="MOCK_MODE")
    request_delay: float = Field(default=0.5, env="REQUEST_DELAY")
    log_to_file: bool = Field(default=False, env="LOG_TO_FILE")
    log_file_path: str = Field(default="./logs/app.log", env="LOG_FILE_PATH")
    
    # ============================================
    # Валидация и вычисляемые свойства
    # ============================================
    
    @property
    def redis_url(self) -> str:
        """Возвращает URL для подключения к Redis."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def api_url(self) -> str:
        """Возвращает базовый URL API."""
        return f"http://{self.api_host}:{self.api_port}"
    
    @property
    def streamlit_url(self) -> str:
        """Возвращает URL Streamlit интерфейса."""
        return f"http://{self.streamlit_host}:{self.streamlit_port}"
    
    @validator("hh_user_agent")
    def validate_hh_user_agent(cls, v):
        """Валидирует User-Agent для HH.ru API."""
        if not v or v == "CareerAggregator/1.0 (anonymous@example.com)":
            logger.warning(
                "HH_USER_AGENT не настроен. Используется значение по умолчанию. "
                "Рекомендуется указать реальный email для связи."
            )
        return v
    
    @validator("deepseek_api_key")
    def validate_deepseek_api_key(cls, v, values):
        """Валидирует API ключ DeepSeek."""
        if not v and not values.get("mock_mode"):
            logger.warning(
                "DEEPSEEK_API_KEY не настроен. LLM парсинг будет отключен. "
                "Будет использоваться rule-based парсинг."
            )
        return v
    
    @validator("relevance_threshold")
    def validate_relevance_threshold(cls, v):
        """Валидирует порог релевантности."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("relevance_threshold должен быть между 0.0 и 1.0")
        return v
    
    class Config:
        """Конфигурация Pydantic."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Глобальный экземпляр настроек
settings = Settings()


def get_settings() -> Settings:
    """
    Возвращает экземпляр настроек.
    
    Используется для dependency injection в FastAPI.
    """
    return settings


def print_settings_summary():
    """Выводит сводку настроек (без чувствительных данных)."""
    summary = {
        "app": f"{settings.app_name} v{settings.app_version}",
        "debug": settings.debug,
        "log_level": settings.log_level,
        "hh_api": {
            "base_url": str(settings.hh_api_base_url),
            "user_agent_set": bool(settings.hh_user_agent and 
                                  settings.hh_user_agent != "CareerAggregator/1.0 (anonymous@example.com)"),
            "max_vacancies": settings.hh_max_vacancies_per_request,
        },
        "llm": {
            "enabled": bool(settings.deepseek_api_key),
            "model": settings.llm_model,
        },
        "embeddings": {
            "model": settings.embedding_model,
            "device": settings.embedding_device,
        },
        "cache": {
            "enabled": settings.cache_enabled,
            "redis_host": settings.redis_host,
            "redis_port": settings.redis_port,
            "ttl_seconds": settings.redis_cache_ttl,
        },
        "api": {
            "host": settings.api_host,
            "port": settings.api_port,
            "url": settings.api_url,
        },
        "streamlit": {
            "host": settings.streamlit_host,
            "port": settings.streamlit_port,
            "url": settings.streamlit_url,
        },
        "search": {
            "relevance_threshold": settings.relevance_threshold,
            "max_results": settings.max_results_to_return,
        },
        "development": {
            "mock_mode": settings.mock_mode,
            "request_delay": settings.request_delay,
        }
    }
    
    return summary


if __name__ == "__main__":
    # При запуске модуля напрямую выводим сводку настроек
    import json
    summary = print_settings_summary()
    print(json.dumps(summary, indent=2, default=str))