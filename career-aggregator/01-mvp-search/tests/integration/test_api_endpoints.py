"""
Интеграционные тесты для API endpoints Career Aggregator 2.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

from app.api.main import app
from app.core.config import Settings


class TestHealthEndpoints:
    """Тесты для health endpoints."""
    
    @pytest.fixture
    def client(self):
        """Фикстура тестового клиента."""
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Тест endpoint /api/health."""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
    
    def test_health_detailed_endpoint(self, client):
        """Тест endpoint /api/health/detailed."""
        with patch('app.api.endpoints.health.get_settings') as mock_settings:
            # Настраиваем мок-настройки
            settings = Mock()
            settings.debug = True
            settings.log_level = "DEBUG"
            mock_settings.return_value = settings
            
            # Настраиваем мок-зависимости
            with patch('app.api.endpoints.health.check_redis_health') as mock_redis:
                with patch('app.api.endpoints.health.check_hh_api_health') as mock_hh:
                    with patch('app.api.endpoints.health.check_embeddings_health') as mock_emb:
                        with patch('app.api.endpoints.health.check_llm_health') as mock_llm:
                            
                            mock_redis.return_value = {"status": "healthy", "hit_rate": 0.75}
                            mock_hh.return_value = {"status": "healthy", "response_time": 150}
                            mock_emb.return_value = {"status": "healthy", "model": "all-MiniLM-L6-v2"}
                            mock_llm.return_value = {"status": "healthy", "model": "deepseek-chat"}
                            
                            response = client.get("/api/health/detailed")
                            
                            assert response.status_code == 200
                            data = response.json()
                            
                            assert "status" in data
                            assert "dependencies" in data
                            assert "cache" in data
                            assert "settings" in data
                            
                            deps = data["dependencies"]
                            assert "redis" in deps
                            assert "hh_api" in deps
                            assert "embeddings" in deps
                            assert "llm" in deps


class TestSearchEndpoints:
    """Тесты для search endpoints."""
    
    @pytest.fixture
    def client(self):
        """Фикстура тестового клиента."""
        return TestClient(app)
    
    def test_search_endpoint_success(self, client):
        """Тест успешного поиска через endpoint /api/search."""
        # Мок-данные для поиска
        mock_vacancies = [
            {
                "id": "12345678",
                "name": "Python разработчик",
                "alternate_url": "https://hh.ru/vacancy/12345678",
                "employer": "Технологическая компания",
                "area": "Москва",
                "salary": {"from": 150000, "to": 250000, "currency": "RUR"},
                "experience": "От 3 до 6 лет",
                "schedule": "Полный день",
                "description": "Требуется опытный Python разработчик",
                "key_skills": ["Python", "Django", "PostgreSQL"],
                "published_at": "2024-01-15T10:30:00+0300",
                "relevance_score": 0.85,
            }
        ]
        
        with patch('app.api.endpoints.search.search_vacancies') as mock_search:
            mock_search.return_value = {
                "vacancies": mock_vacancies,
                "total_results": 100,
                "returned_results": 1,
                "cache_hit": False,
                "processing_time": 200,
                "search_params": {
                    "query": "python разработчик",
                    "filters": {},
                    "limit": 50,
                    "use_semantic": True,
                },
            }
            
            # Выполняем запрос
            payload = {
                "query": "python разработчик",
                "filters": {},
                "limit": 50,
                "use_semantic": True,
            }
            
            response = client.post("/api/search", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            
            assert "vacancies" in data
            assert len(data["vacancies"]) == 1
            assert data["total_results"] == 100
            assert data["returned_results"] == 1
            assert data["cache_hit"] is False
            assert "processing_time" in data
            assert "search_params" in data
    
    def test_search_endpoint_with_filters(self, client):
        """Тест поиска с фильтрами через endpoint /api/search."""
        with patch('app.api.endpoints.search.search_vacancies') as mock_search:
            mock_search.return_value = {
                "vacancies": [],
                "total_results": 0,
                "returned_results": 0,
                "cache_hit": False,
                "processing_time": 100,
                "search_params": {},
            }
            
            # Выполняем запрос с фильтрами
            payload = {
                "query": "python разработчик москва senior",
                "filters": {
                    "area": "1",
                    "experience": "senior",
                    "schedule": "full_day",
                    "salary_from": 200000,
                    "currency": "RUR",
                },
                "limit": 30,
                "use_semantic": False,
            }
            
            response = client.post("/api/search", json=payload)
            
            assert response.status_code == 200
            # Проверяем, что функция поиска была вызвана с правильными параметрами
            mock_search.assert_called_once()
    
    def test_search_endpoint_empty_query(self, client):
        """Тест поиска с пустым запросом."""
        payload = {
            "query": "",
            "filters": {},
            "limit": 50,
            "use_semantic": True,
        }
        
        response = client.post("/api/search", json=payload)
        
        # Должна быть ошибка валидации
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_search_endpoint_invalid_limit(self, client):
        """Тест поиска с невалидным лимитом."""
        payload = {
            "query": "python",
            "filters": {},
            "limit": 200,  # Превышает максимальный лимит
            "use_semantic": True,
        }
        
        response = client.post("/api/search", json=payload)
        
        # Должна быть ошибка валидации
        assert response.status_code == 422


class TestFiltersEndpoints:
    """Тесты для filters endpoints."""
    
    @pytest.fixture
    def client(self):
        """Фикстура тестового клиента."""
        return TestClient(app)
    
    def test_filters_endpoint_success(self, client):
        """Тест успешного получения фильтров через endpoint /api/filters."""
        mock_areas = [
            {"id": "1", "name": "Москва"},
            {"id": "2", "name": "Санкт-Петербург"},
        ]
        
        mock_experience = [
            {"id": "noExperience", "name": "Нет опыта"},
            {"id": "between1And3", "name": "От 1 года до 3 лет"},
        ]
        
        mock_schedules = [
            {"id": "fullDay", "name": "Полный день"},
            {"id": "remote", "name": "Удаленная работа"},
        ]
        
        with patch('app.api.endpoints.filters.get_areas') as mock_get_areas:
            with patch('app.api.endpoints.filters.get_experience_levels') as mock_get_exp:
                with patch('app.api.endpoints.filters.get_schedules') as mock_get_sched:
                    
                    mock_get_areas.return_value = mock_areas
                    mock_get_exp.return_value = mock_experience
                    mock_get_sched.return_value = mock_schedules
                    
                    response = client.get("/api/filters")
                    
                    assert response.status_code == 200
                    data = response.json()
                    
                    assert "areas" in data
                    assert "experience_levels" in data
                    assert "schedules" in data
                    
                    assert len(data["areas"]) == 2
                    assert len(data["experience_levels"]) == 2
                    assert len(data["schedules"]) == 2
    
    def test_filters_endpoint_with_error(self, client):
        """Тест получения фильтров с ошибкой."""
        with patch('app.api.endpoints.filters.get_areas') as mock_get_areas:
            mock_get_areas.side_effect = Exception("API error")
            
            response = client.get("/api/filters")
            
            # Должен вернуться пустой результат или ошибка
            assert response.status_code == 200  # Или 500 в зависимости от реализации
            data = response.json()
            # Проверяем структуру ответа даже при ошибке
            assert "areas" in data
            assert "experience_levels" in data
            assert "schedules" in data


class TestCacheEndpoints:
    """Тесты для cache endpoints."""
    
    @pytest.fixture
    def client(self):
        """Фикстура тестового клиента."""
        return TestClient(app)
    
    def test_cache_stats_endpoint(self, client):
        """Тест endpoint /api/cache/stats."""
        mock_stats = {
            "total_keys": 150,
            "hit_rate": 0.75,
            "memory_used": "45.2 MB",
            "uptime": "2 days, 3 hours",
        }
        
        with patch('app.api.endpoints.cache.get_cache_stats') as mock_get_stats:
            mock_get_stats.return_value = mock_stats
            
            response = client.get("/api/cache/stats")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "total_keys" in data
            assert "hit_rate" in data
            assert "memory_used" in data
            assert "uptime" in data
    
    def test_cache_clear_endpoint(self, client):
        """Тест endpoint /api/cache/clear."""
        mock_result = {
            "cleared": True,
            "keys_cleared": 150,
            "message": "Cache cleared successfully",
        }
        
        with patch('app.api.endpoints.cache.clear_cache') as mock_clear:
            mock_clear.return_value = mock_result
            
            response = client.post("/api/cache/clear")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["cleared"] is True
            assert data["keys_cleared"] == 150
            assert "message" in data
    
    def test_cache_invalidate_endpoint(self, client):
        """Тест endpoint /api/cache/invalidate."""
        mock_result = {
            "invalidated": True,
            "pattern": "search:*",
            "keys_invalidated": 50,
        }
        
        with patch('app.api.endpoints.cache.invalidate_cache_pattern') as mock_invalidate:
            mock_invalidate.return_value = mock_result
            
            payload = {"pattern": "search:*"}
            response = client.post("/api/cache/invalidate", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["invalidated"] is True
            assert data["pattern"] == "search:*"
            assert data["keys_invalidated"] == 50
    
    def test_cache_invalidate_empty_pattern(self, client):
        """Тест инвалидации кэша с пустым паттерном."""
        payload = {"pattern": ""}
        response = client.post("/api/cache/invalidate", json=payload)
        
        # Должна быть ошибка валидации
        assert response.status_code == 422


class TestAPIErrorHandling:
    """Тесты обработки ошибок API."""
    
    @pytest.fixture
    def client(self):
        """Фикстура тестового клиента."""
        return TestClient(app)
    
    def test_not_found_endpoint(self, client):
        """Тест обращения к несуществующему endpoint."""
        response = client.get("/api/nonexistent")
        
        assert response.status_code == 404
    
    def test_method_not_allowed(self, client):
        """Тест использования неподдерживаемого метода HTTP."""
        response = client.put("/api/health")
        
        assert response.status_code == 405  # Method Not Allowed
    
    def test_invalid_json_payload(self, client):
        """Тест отправки невалидного JSON."""
        response = client.post("/api/search", data="invalid json")
        
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_rate_limiting(self, client):
        """Тест ограничения частоты запросов (если реализовано)."""
        # Этот тест зависит от реализации rate limiting
        # Если rate limiting не реализован, endpoint должен работать нормально
        for i in range(5):
            response = client.get("/api/health")
            # Все запросы должны успешно обрабатываться
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])