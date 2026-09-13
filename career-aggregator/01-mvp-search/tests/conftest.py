"""
Конфигурация pytest для тестов Career Aggregator 2.

Этот файл содержит фикстуры и настройки для всех тестов.
"""

import pytest
import asyncio
from typing import Dict, Any, AsyncGenerator
from unittest.mock import AsyncMock, Mock, patch

from app.core.config import Settings


@pytest.fixture
def settings() -> Settings:
    """Фикстура настроек для тестов."""
    return Settings(
        hh_api_base_url="https://api.hh.ru",
        hh_api_timeout=10,
        hh_api_max_retries=3,
        embeddings_model_name="sentence-transformers/all-MiniLM-L6-v2",
        llm_api_key="test-key",
        llm_api_base_url="https://api.deepseek.com",
        llm_model_name="deepseek-chat",
        redis_url="redis://localhost:6379",
        redis_cache_ttl=3600,
        api_host="127.0.0.1",
        api_port=8000,
        debug=True,
        log_level="DEBUG",
    )


@pytest.fixture
def mock_hh_vacancy() -> Dict[str, Any]:
    """Фикстура мок-вакансии HH.ru."""
    return {
        "id": "12345678",
        "name": "Python разработчик",
        "alternate_url": "https://hh.ru/vacancy/12345678",
        "employer": {
            "id": "12345",
            "name": "Технологическая компания",
        },
        "area": {
            "id": "1",
            "name": "Москва",
        },
        "salary": {
            "from": 150000,
            "to": 250000,
            "currency": "RUR",
        },
        "experience": {
            "id": "between3And6",
            "name": "От 3 до 6 лет",
        },
        "schedule": {
            "id": "fullDay",
            "name": "Полный день",
        },
        "description": "Требуется опытный Python разработчик для работы над высоконагруженным проектом.",
        "key_skills": [
            {"name": "Python"},
            {"name": "Django"},
            {"name": "PostgreSQL"},
            {"name": "Docker"},
        ],
        "published_at": "2024-01-15T10:30:00+0300",
    }


@pytest.fixture
def mock_search_response() -> Dict[str, Any]:
    """Фикстура мок-ответа поиска HH.ru."""
    return {
        "items": [
            {
                "id": "12345678",
                "name": "Python разработчик",
                "alternate_url": "https://hh.ru/vacancy/12345678",
                "employer": {"name": "Технологическая компания"},
                "area": {"name": "Москва"},
                "salary": {"from": 150000, "to": 250000, "currency": "RUR"},
                "experience": {"name": "От 3 до 6 лет"},
                "schedule": {"name": "Полный день"},
                "snippet": {"requirement": "Требуется опытный Python разработчик"},
            }
        ],
        "found": 100,
        "pages": 5,
        "per_page": 20,
        "page": 0,
    }


@pytest.fixture
def mock_llm_response() -> Dict[str, Any]:
    """Фикстура мок-ответа LLM."""
    return {
        "choices": [
            {
                "message": {
                    "content": '{"profession": "python разработчик", "location": "москва", "experience": "senior", "schedule": "full_day"}'
                }
            }
        ]
    }


@pytest.fixture
def mock_embeddings_response() -> list:
    """Фикстура мок-ответа эмбеддингов."""
    return [0.1, 0.2, 0.3, 0.4, 0.5] * 20  # 100-мерный вектор


@pytest.fixture
def event_loop():
    """Фикстура для работы с asyncio в тестах."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_redis_client() -> AsyncMock:
    """Фикстура мок-клиента Redis."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=0)
    mock.ttl = AsyncMock(return_value=3600)
    return mock


@pytest.fixture
def mock_requests_session():
    """Фикстура мок-сессии requests."""
    with patch('requests.Session') as mock_session:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_session.return_value.request.return_value = mock_response
        yield mock_session


@pytest.fixture
def mock_aiohttp_client():
    """Фикстура мок-клиента aiohttp."""
    with patch('aiohttp.ClientSession') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"status": "ok"})
        mock_response.text = AsyncMock(return_value='{"status": "ok"}')
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None
        
        mock_session.return_value.__aenter__.return_value = mock_session.return_value
        mock_session.return_value.get.return_value = mock_response
        mock_session.return_value.post.return_value = mock_response
        yield mock_session