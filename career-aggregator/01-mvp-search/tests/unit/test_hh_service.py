"""
Тесты для сервиса HH.ru клиента.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

from app.services.hh.client import HHClient
from app.models.hh import HHVacancySearchParams


class TestHHClient:
    """Тесты для HH.ru клиента."""
    
    @pytest.fixture
    def mock_settings(self):
        """Фикстура настроек."""
        settings = Mock()
        settings.hh_api_base_url = "https://api.hh.ru"
        settings.hh_api_timeout = 10
        settings.hh_api_max_retries = 3
        return settings
    
    @pytest.fixture
    def mock_search_response(self):
        """Фикстура мок-ответа поиска."""
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
    
    @pytest.mark.asyncio
    async def test_search_vacancies_success(self, mock_settings, mock_search_response):
        """Тест успешного поиска вакансий."""
        with patch('aiohttp.ClientSession') as mock_session:
            # Настраиваем мок-ответ
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_search_response)
            mock_response.__aenter__.return_value = mock_response
            mock_response.__aexit__.return_value = None
            
            mock_session.return_value.__aenter__.return_value.get.return_value = mock_response
            
            # Создаем клиент
            client = HHClient(mock_settings)
            
            # Выполняем поиск
            params = HHVacancySearchParams(text="python разработчик")
            result = await client.search_vacancies(params)
            
            # Проверяем результат
            assert result is not None
            assert len(result.items) == 1
            assert result.items[0].name == "Python разработчик"
            assert result.found == 100
            assert result.pages == 5
    
    @pytest.mark.asyncio
    async def test_search_vacancies_empty_result(self, mock_settings):
        """Тест поиска с пустым результатом."""
        with patch('aiohttp.ClientSession') as mock_session:
            # Настраиваем мок-ответ с пустым результатом
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"items": [], "found": 0, "pages": 0})
            mock_response.__aenter__.return_value = mock_response
            mock_response.__aexit__.return_value = None
            
            mock_session.return_value.__aenter__.return_value.get.return_value = mock_response
            
            # Создаем клиент
            client = HHClient(mock_settings)
            
            # Выполняем поиск
            params = HHVacancySearchParams(text="несуществующая вакансия")
            result = await client.search_vacancies(params)
            
            # Проверяем результат
            assert result is not None
            assert len(result.items) == 0
            assert result.found == 0
            assert result.pages == 0
    
    @pytest.mark.asyncio
    async def test_search_vacancies_api_error(self, mock_settings):
        """Тест поиска с ошибкой API."""
        with patch('aiohttp.ClientSession') as mock_session:
            # Настраиваем мок-ответ с ошибкой
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value="Internal Server Error")
            mock_response.__aenter__.return_value = mock_response
            mock_response.__aexit__.return_value = None
            
            mock_session.return_value.__aenter__.return_value.get.return_value = mock_response
            
            # Создаем клиент
            client = HHClient(mock_settings)
            
            # Выполняем поиск (должен вернуть None из-за ошибки)
            params = HHVacancySearchParams(text="python")
            result = await client.search_vacancies(params)
            
            # Проверяем, что результат None
            assert result is None
    
    @pytest.mark.asyncio
    async def test_search_vacancies_retry_logic(self, mock_settings):
        """Тест логики повторных попыток при ошибках."""
        call_count = 0
        
        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            mock_response = AsyncMock()
            if call_count < 3:  # Первые две попытки неудачные
                mock_response.status = 429  # Too Many Requests
                mock_response.text = AsyncMock(return_value="Rate limit exceeded")
            else:  # Третья попытка успешная
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value={"items": [], "found": 0, "pages": 0})
            
            mock_response.__aenter__.return_value = mock_response
            mock_response.__aexit__.return_value = None
            return mock_response
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.get = mock_get
            
            # Создаем клиент с 3 попытками
            client = HHClient(mock_settings)
            
            # Выполняем поиск
            params = HHVacancySearchParams(text="python")
            result = await client.search_vacancies(params)
            
            # Проверяем, что было 3 попытки
            assert call_count == 3
            # Проверяем, что в итоге получили результат (пустой)
            assert result is not None
            assert result.found == 0
    
    @pytest.mark.asyncio
    async def test_get_vacancy_by_id_success(self, mock_settings):
        """Тест успешного получения вакансии по ID."""
        vacancy_data = {
            "id": "12345678",
            "name": "Python разработчик",
            "alternate_url": "https://hh.ru/vacancy/12345678",
            "employer": {"id": "12345", "name": "Технологическая компания"},
            "area": {"id": "1", "name": "Москва"},
            "salary": {"from": 150000, "to": 250000, "currency": "RUR"},
            "experience": {"id": "between3And6", "name": "От 3 до 6 лет"},
            "schedule": {"id": "fullDay", "name": "Полный день"},
            "description": "Требуется опытный Python разработчик",
            "key_skills": [{"name": "Python"}, {"name": "Django"}],
            "published_at": "2024-01-15T10:30:00+0300",
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            # Настраиваем мок-ответ
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=vacancy_data)
            mock_response.__aenter__.return_value = mock_response
            mock_response.__aexit__.return_value = None
            
            mock_session.return_value.__aenter__.return_value.get.return_value = mock_response
            
            # Создаем клиент
            client = HHClient(mock_settings)
            
            # Получаем вакансию
            vacancy = await client.get_vacancy_by_id("12345678")
            
            # Проверяем результат
            assert vacancy is not None
            assert vacancy.id == "12345678"
            assert vacancy.name == "Python разработчик"
            assert vacancy.employer.name == "Технологическая компания"
            assert vacancy.area.name == "Москва"
            assert len(vacancy.key_skills) == 2
    
    @pytest.mark.asyncio
    async def test_get_vacancy_by_id_not_found(self, mock_settings):
        """Тест получения несуществующей вакансии."""
        with patch('aiohttp.ClientSession') as mock_session:
            # Настраиваем мок-ответ с 404
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_response.text = AsyncMock(return_value="Not Found")
            mock_response.__aenter__.return_value = mock_response
            mock_response.__aexit__.return_value = None
            
            mock_session.return_value.__aenter__.return_value.get.return_value = mock_response
            
            # Создаем клиент
            client = HHClient(mock_settings)
            
            # Пытаемся получить вакансию
            vacancy = await client.get_vacancy_by_id("99999999")
            
            # Проверяем, что результат None
            assert vacancy is None
    
    @pytest.mark.asyncio
    async def test_get_areas_success(self, mock_settings):
        """Тест успешного получения списка регионов."""
        areas_data = [
            {"id": "1", "name": "Москва"},
            {"id": "2", "name": "Санкт-Петербург"},
            {"id": "3", "name": "Новосибирск"},
        ]
        
        with patch('aiohttp.ClientSession') as mock_session:
            # Настраиваем мок-ответ
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=areas_data)
            mock_response.__aenter__.return_value = mock_response
            mock_response.__aexit__.return_value = None
            
            mock_session.return_value.__aenter__.return_value.get.return_value = mock_response
            
            # Создаем клиент
            client = HHClient(mock_settings)
            
            # Получаем регионы
            areas = await client.get_areas()
            
            # Проверяем результат
            assert areas is not None
            assert len(areas) == 3
            assert areas[0].name == "Москва"
            assert areas[1].name == "Санкт-Петербург"
            assert areas[2].name == "Новосибирск"
    
    @pytest.mark.asyncio
    async def test_get_experience_levels_success(self, mock_settings):
        """Тест успешного получения уровней опыта."""
        experience_data = [
            {"id": "noExperience", "name": "Нет опыта"},
            {"id": "between1And3", "name": "От 1 года до 3 лет"},
            {"id": "between3And6", "name": "От 3 до 6 лет"},
            {"id": "moreThan6", "name": "Более 6 лет"},
        ]
        
        with patch('aiohttp.ClientSession') as mock_session:
            # Настраиваем мок-ответ
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=experience_data)
            mock_response.__aenter__.return_value = mock_response
            mock_response.__aexit__.return_value = None
            
            mock_session.return_value.__aenter__.return_value.get.return_value = mock_response
            
            # Создаем клиент
            client = HHClient(mock_settings)
            
            # Получаем уровни опыта
            experience_levels = await client.get_experience_levels()
            
            # Проверяем результат
            assert experience_levels is not None
            assert len(experience_levels) == 4
            assert experience_levels[0].name == "Нет опыта"
            assert experience_levels[3].name == "Более 6 лет"
    
    @pytest.mark.asyncio
    async def test_get_schedules_success(self, mock_settings):
        """Тест успешного получения графиков работы."""
        schedules_data = [
            {"id": "fullDay", "name": "Полный день"},
            {"id": "shift", "name": "Сменный график"},
            {"id": "flexible", "name": "Гибкий график"},
            {"id": "remote", "name": "Удаленная работа"},
            {"id": "flyInFlyOut", "name": "Вахтовый метод"},
        ]
        
        with patch('aiohttp.ClientSession') as mock_session:
            # Настраиваем мок-ответ
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=schedules_data)
            mock_response.__aenter__.return_value = mock_response
            mock_response.__aexit__.return_value = None
            
            mock_session.return_value.__aenter__.return_value.get.return_value = mock_response
            
            # Создаем клиент
            client = HHClient(mock_settings)
            
            # Получаем графики работы
            schedules = await client.get_schedules()
            
            # Проверяем результат
            assert schedules is not None
            assert len(schedules) == 5
            assert schedules[0].name == "Полный день"
            assert schedules[3].name == "Удаленная работа"


class TestHHClientIntegration:
    """Интеграционные тесты для HH.ru клиента."""
    
    def test_build_search_url(self, mock_settings):
        """Тест построения URL для поиска."""
        client = HHClient(mock_settings)
        
        # Простой запрос
        params1 = HHVacancySearchParams(text="python")
        url1 = client._build_search_url(params1)
        assert "text=python" in url1
        assert "per_page=100" in url1
        
        # Запрос с фильтрами
        params2 = HHVacancySearchParams(
            text="python разработчик",
            area="1",
            experience="between3And6",
            schedule="fullDay",
            salary=200000,
            currency="RUR",
            per_page=50,
            page=2,
        )
        url2 = client._build_search_url(params2)
        assert "text=python+разработчик" in url2
        assert "area=1" in url2
        assert "experience=between3And6" in url2
        assert "schedule=fullDay" in url2
        assert "salary=200000" in url2
        assert "currency=RUR" in url2
        assert "per_page=50" in url2
        assert "page=2" in url2
    
    def test_parse_vacancy_from_api(self, mock_settings):
        """Тест парсинга вакансии из API ответа."""
        client = HHClient(mock_settings)
        
        api_data = {
            "id": "12345678",
            "name": "Python разработчик",
            "alternate_url": "https://hh.ru/vacancy/12345678",
            "employer": {"id": "12345", "name": "Технологическая компания"},
            "area": {"id": "1", "name": "Москва"},
            "salary": {"from": 150000, "to": 250000, "currency": "RUR"},
            "experience": {"id": "between3And6", "name": "От 3 до 6 лет"},
            "schedule": {"id": "fullDay", "name": "Полный день"},
            "description": "Требуется опытный Python разработчик",
            "key_skills": [{"name": "Python"}, {"name": "Django"}],
            "published_at": "2024-01-15T10:30:00+0300",
        }
        
        vacancy = client._parse_vacancy_from_api(api_data)
        
        assert vacancy.id == "12345678"
        assert vacancy.name == "Python разработчик"
        assert vacancy.employer.name == "Технологическая компания"
        assert vacancy.area.name == "Москва"
        assert vacancy.salary.from_ == 150000
        assert vacancy.salary.to == 250000
        assert vacancy.experience.name == "От 3 до 6 лет"
        assert vacancy.schedule.name == "Полный день"
        assert len(vacancy.key_skills) == 2
    
    def test_parse_vacancy_without_salary(self, mock_settings):
        """Тест парсинга вакансии без зарплаты."""
        client = HHClient(mock_settings)
        
        api_data = {
            "id": "12345678",
            "name": "Python разработчик",
            "alternate_url": "https://hh.ru/vacancy/12345678",
            "employer": {"id": "12345", "name": "Компания"},
            "area": {"id": "1", "name": "Москва"},
            "salary": None,
            "experience": {"id": "noExperience", "name": "Нет опыта"},
            "schedule": {"id": "fullDay", "name": "Полный день"},
            "description": "Описание",
            "key_skills": [],
            "published_at": "2024-01-15T10:30:00+0300",
        }
        
        vacancy = client._parse_vacancy_from_api(api_data)
        
        assert vacancy.id == "12345678"
        assert vacancy.salary is None
        assert vacancy.experience.name == "Нет опыта"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])