"""
Тесты для моделей данных Career Aggregator 2.
"""

import pytest
from datetime import datetime
from app.models.hh import (
    HHVacancy,
    HHVacancySearchParams,
    HHEmployer,
    HHArea,
    HHSalary,
    HHExperience,
    HHSchedule,
    HHKeySkill,
    SearchQuery,
    SearchFilters,
    SearchResult,
    VacancyWithRelevance,
)


class TestHHModels:
    """Тесты для моделей HH.ru."""
    
    def test_hh_vacancy_creation(self):
        """Тест создания модели вакансии."""
        vacancy = HHVacancy(
            id="12345678",
            name="Python разработчик",
            alternate_url="https://hh.ru/vacancy/12345678",
            employer=HHEmployer(id="12345", name="Технологическая компания"),
            area=HHArea(id="1", name="Москва"),
            salary=HHSalary(from_=150000, to=250000, currency="RUR"),
            experience=HHExperience(id="between3And6", name="От 3 до 6 лет"),
            schedule=HHSchedule(id="fullDay", name="Полный день"),
            description="Требуется опытный Python разработчик",
            key_skills=[HHKeySkill(name="Python"), HHKeySkill(name="Django")],
            published_at="2024-01-15T10:30:00+0300",
        )
        
        assert vacancy.id == "12345678"
        assert vacancy.name == "Python разработчик"
        assert vacancy.employer.name == "Технологическая компания"
        assert vacancy.area.name == "Москва"
        assert vacancy.salary.from_ == 150000
        assert vacancy.salary.to == 250000
        assert len(vacancy.key_skills) == 2
        assert vacancy.key_skills[0].name == "Python"
    
    def test_hh_vacancy_without_salary(self):
        """Тест создания вакансии без зарплаты."""
        vacancy = HHVacancy(
            id="12345678",
            name="Python разработчик",
            alternate_url="https://hh.ru/vacancy/12345678",
            employer=HHEmployer(id="12345", name="Компания"),
            area=HHArea(id="1", name="Москва"),
            salary=None,
            experience=HHExperience(id="noExperience", name="Нет опыта"),
            schedule=HHSchedule(id="fullDay", name="Полный день"),
            description="Описание",
            key_skills=[],
            published_at="2024-01-15T10:30:00+0300",
        )
        
        assert vacancy.salary is None
    
    def test_hh_vacancy_search_params(self):
        """Тест создания параметров поиска."""
        params = HHVacancySearchParams(
            text="python разработчик москва",
            area="1",
            experience="between3And6",
            schedule="fullDay",
            salary=200000,
            currency="RUR",
            per_page=50,
            page=0,
        )
        
        assert params.text == "python разработчик москва"
        assert params.area == "1"
        assert params.experience == "between3And6"
        assert params.salary == 200000
        assert params.per_page == 50
        assert params.page == 0
    
    def test_hh_vacancy_search_params_defaults(self):
        """Тест параметров поиска с значениями по умолчанию."""
        params = HHVacancySearchParams(text="python")
        
        assert params.text == "python"
        assert params.area is None
        assert params.experience is None
        assert params.schedule is None
        assert params.salary is None
        assert params.currency == "RUR"
        assert params.per_page == 100
        assert params.page == 0


class TestSearchModels:
    """Тесты для моделей поиска."""
    
    def test_search_query_creation(self):
        """Тест создания поискового запроса."""
        query = SearchQuery(
            query="python разработчик senior москва",
            filters=SearchFilters(
                area="1",
                experience="senior",
                schedule="full_day",
                salary_from=200000,
                currency="RUR",
            ),
            limit=50,
            use_semantic=True,
        )
        
        assert query.query == "python разработчик senior москва"
        assert query.filters.area == "1"
        assert query.filters.experience == "senior"
        assert query.filters.salary_from == 200000
        assert query.limit == 50
        assert query.use_semantic is True
    
    def test_search_filters_defaults(self):
        """Тест фильтров поиска с значениями по умолчанию."""
        filters = SearchFilters()
        
        assert filters.area is None
        assert filters.experience is None
        assert filters.schedule is None
        assert filters.salary_from is None
        assert filters.currency == "RUR"
    
    def test_vacancy_with_relevance(self):
        """Тест создания вакансии с релевантностью."""
        vacancy = VacancyWithRelevance(
            id="12345678",
            name="Python разработчик",
            alternate_url="https://hh.ru/vacancy/12345678",
            employer="Технологическая компания",
            area="Москва",
            salary={"from": 150000, "to": 250000, "currency": "RUR"},
            experience="От 3 до 6 лет",
            schedule="Полный день",
            description="Требуется опытный Python разработчик",
            key_skills=["Python", "Django", "PostgreSQL"],
            published_at="2024-01-15T10:30:00+0300",
            relevance_score=0.85,
        )
        
        assert vacancy.id == "12345678"
        assert vacancy.relevance_score == 0.85
        assert len(vacancy.key_skills) == 3
    
    def test_search_result_creation(self):
        """Тест создания результата поиска."""
        vacancies = [
            VacancyWithRelevance(
                id="1",
                name="Вакансия 1",
                alternate_url="https://hh.ru/vacancy/1",
                employer="Компания 1",
                area="Москва",
                salary=None,
                experience="От 1 до 3 лет",
                schedule="Полный день",
                description="Описание 1",
                key_skills=["Python"],
                published_at="2024-01-15T10:30:00+0300",
                relevance_score=0.9,
            ),
            VacancyWithRelevance(
                id="2",
                name="Вакансия 2",
                alternate_url="https://hh.ru/vacancy/2",
                employer="Компания 2",
                area="Санкт-Петербург",
                salary={"from": 100000, "currency": "RUR"},
                experience="Нет опыта",
                schedule="Удаленная работа",
                description="Описание 2",
                key_skills=["JavaScript"],
                published_at="2024-01-14T09:00:00+0300",
                relevance_score=0.7,
            ),
        ]
        
        result = SearchResult(
            vacancies=vacancies,
            total_results=100,
            returned_results=2,
            cache_hit=False,
            processing_time=150,
            search_params={
                "query": "python",
                "filters": {},
                "limit": 50,
                "use_semantic": True,
            },
        )
        
        assert len(result.vacancies) == 2
        assert result.total_results == 100
        assert result.returned_results == 2
        assert result.cache_hit is False
        assert result.processing_time == 150
        assert result.search_params["query"] == "python"
    
    def test_search_result_with_cache_hit(self):
        """Тест результата поиска с попаданием в кэш."""
        result = SearchResult(
            vacancies=[],
            total_results=0,
            returned_results=0,
            cache_hit=True,
            processing_time=10,
            search_params={},
        )
        
        assert result.cache_hit is True
        assert result.processing_time == 10


class TestModelValidation:
    """Тесты валидации моделей."""
    
    def test_salary_validation(self):
        """Тест валидации зарплаты."""
        # Зарплата только "от"
        salary1 = HHSalary(from_=100000, to=None, currency="RUR")
        assert salary1.from_ == 100000
        assert salary1.to is None
        
        # Зарплата только "до"
        salary2 = HHSalary(from_=None, to=200000, currency="USD")
        assert salary2.from_ is None
        assert salary2.to == 200000
        assert salary2.currency == "USD"
        
        # Зарплата в диапазоне
        salary3 = HHSalary(from_=150000, to=250000, currency="EUR")
        assert salary3.from_ == 150000
        assert salary3.to == 250000
    
    def test_experience_validation(self):
        """Тест валидации опыта."""
        experience = HHExperience(id="between3And6", name="От 3 до 6 лет")
        assert experience.id == "between3And6"
        assert experience.name == "От 3 до 6 лет"
    
    def test_schedule_validation(self):
        """Тест валидации графика работы."""
        schedule = HHSchedule(id="remote", name="Удаленная работа")
        assert schedule.id == "remote"
        assert schedule.name == "Удаленная работа"
    
    def test_key_skills_validation(self):
        """Тест валидации ключевых навыков."""
        skills = [
            HHKeySkill(name="Python"),
            HHKeySkill(name="Django"),
            HHKeySkill(name="FastAPI"),
        ]
        
        assert len(skills) == 3
        assert skills[0].name == "Python"
        assert skills[1].name == "Django"
        assert skills[2].name == "FastAPI"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])