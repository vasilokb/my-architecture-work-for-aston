"""
Модели данных для HH.ru API.

Этот модуль содержит Pydantic модели для представления данных
из HH.ru API и их преобразования во внутренний формат.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


# ============================================
# Базовые модели
# ============================================

class Salary(BaseModel):
    """Модель зарплаты."""
    from_: Optional[float] = Field(None, alias="from")
    to: Optional[float] = None
    currency: Optional[str] = None
    gross: Optional[bool] = None
    
    class Config:
        allow_population_by_field_name = True


class Area(BaseModel):
    """Модель региона/города."""
    id: str
    name: str
    parent_id: Optional[str] = None
    areas: List["Area"] = []


class Specialization(BaseModel):
    """Модель специализации (профессии)."""
    id: str
    name: str
    laboring: bool = False
    specializations: List["Specialization"] = []


class Industry(BaseModel):
    """Модель отрасли."""
    id: str
    name: str


class Schedule(BaseModel):
    """Модель графика работы."""
    id: str
    name: str


class ExperienceLevel(BaseModel):
    """Модель уровня опыта."""
    id: str
    name: str


# ============================================
# Модели вакансий
# ============================================

class Vacancy(BaseModel):
    """Модель вакансии."""
    id: str
    name: str
    employer: str = ""
    employer_url: Optional[str] = None
    salary: Optional[Salary] = None
    area: str = ""
    area_id: Optional[str] = None
    schedule: str = ""
    experience: str = ""
    description: str = ""
    key_skills: List[str] = []
    published_at: Optional[str] = None
    alternate_url: str = ""
    response_url: Optional[str] = None
    archived: bool = False
    type: str = ""
    
    # Дополнительные поля из детального ответа
    branded_description: Optional[str] = None
    contacts: Optional[Dict[str, Any]] = None
    address: Optional[Dict[str, Any]] = None
    department: Optional[Dict[str, Any]] = None
    test: Optional[Dict[str, Any]] = None
    employer_vacancies_url: Optional[str] = None
    
    @property
    def formatted_salary(self) -> Optional[str]:
        """Возвращает отформатированную строку зарплаты."""
        if not self.salary:
            return None
        
        parts = []
        if self.salary.from_ is not None:
            parts.append(f"от {self.salary.from_:,.0f}")
        if self.salary.to is not None:
            parts.append(f"до {self.salary.to:,.0f}")
        
        if not parts:
            return None
        
        result = " ".join(parts)
        if self.salary.currency:
            currency_symbol = {
                "RUR": "₽",
                "USD": "$",
                "EUR": "€",
                "KZT": "₸",
                "BYR": "Br",
                "UAH": "₴",
            }.get(self.salary.currency, self.salary.currency)
            result += f" {currency_symbol}"
        
        return result
    
    @property
    def short_description(self) -> str:
        """Возвращает короткое описание (первые 200 символов)."""
        if not self.description:
            return ""
        
        # Убираем HTML теги и лишние пробелы
        import re
        clean_text = re.sub(r'<[^>]+>', ' ', self.description)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        if len(clean_text) <= 200:
            return clean_text
        
        return clean_text[:197] + "..."
    
    @property
    def skills_string(self) -> str:
        """Возвращает строку с ключевыми навыками."""
        if not self.key_skills:
            return ""
        return ", ".join(self.key_skills[:5])  # Ограничиваем 5 навыками


class VacancySearchParams(BaseModel):
    """Параметры поиска вакансий."""
    text: Optional[str] = None
    area: Optional[str] = None
    specialization: Optional[str] = None
    experience: Optional[str] = None
    schedule: Optional[str] = None
    employment: Optional[str] = None
    salary: Optional[int] = None
    currency: Optional[str] = None
    order_by: Optional[str] = None
    date_from: Optional[datetime] = None
    only_with_salary: bool = False
    
    @validator("text")
    def validate_text(cls, v):
        """Валидирует текстовый запрос."""
        if v and len(v.strip()) < 2:
            raise ValueError("Текстовый запрос должен содержать минимум 2 символа")
        return v.strip() if v else v
    
    @validator("area")
    def validate_area(cls, v):
        """Валидирует ID региона."""
        if v and not v.isdigit():
            raise ValueError("ID региона должен быть числом")
        return v
    
    @validator("salary")
    def validate_salary(cls, v):
        """Валидирует зарплату."""
        if v is not None and v < 0:
            raise ValueError("Зарплата не может быть отрицательной")
        return v


class VacancySearchResponse(BaseModel):
    """Ответ на поиск вакансий."""
    found: int = 0
    vacancies: List[Vacancy] = []
    search_params: VacancySearchParams
    pages_processed: int = 0
    
    @property
    def has_results(self) -> bool:
        """Проверяет, есть ли результаты."""
        return len(self.vacancies) > 0
    
    @property
    def results_count(self) -> int:
        """Возвращает количество найденных вакансий."""
        return len(self.vacancies)


# ============================================
# Модели для семантического поиска
# ============================================

class VacancyWithEmbedding(Vacancy):
    """Вакансия с векторным представлением."""
    embedding: Optional[List[float]] = None
    relevance_score: Optional[float] = None


class SemanticSearchRequest(BaseModel):
    """Запрос на семантический поиск."""
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = Field(default=50, ge=1, le=200)
    use_semantic: bool = True
    
    @validator("query")
    def validate_query(cls, v):
        """Валидирует поисковый запрос."""
        if not v or len(v.strip()) < 2:
            raise ValueError("Поисковый запрос должен содержать минимум 2 символа")
        return v.strip()


class SemanticSearchResponse(BaseModel):
    """Ответ на семантический поиск."""
    query: str
    total_results: int = 0
    returned_results: int = 0
    vacancies: List[VacancyWithEmbedding] = []
    search_params: Optional[Dict[str, Any]] = None
    cache_hit: bool = False
    processing_time: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


# ============================================
# Модели для LLM парсинга
# ============================================

class ParsedQuery(BaseModel):
    """Распарсенный поисковый запрос."""
    profession: Optional[str] = None
    location: Optional[str] = None
    experience: Optional[str] = None
    schedule: Optional[str] = None
    employment: Optional[str] = None
    skills: List[str] = []
    raw_query: str = ""
    
    def to_search_params(self) -> VacancySearchParams:
        """Преобразует распарсенный запрос в параметры поиска."""
        return VacancySearchParams(
            text=self.profession,
            area=self._location_to_area_id(self.location) if self.location else None,
            experience=self._experience_to_hh_format(self.experience) if self.experience else None,
            schedule=self._schedule_to_hh_format(self.schedule) if self.schedule else None,
        )
    
    @staticmethod
    def _location_to_area_id(location: str) -> Optional[str]:
        """Преобразует название локации в ID региона HH.ru."""
        # Это упрощенная реализация. В реальном приложении нужно
        # использовать справочник регионов из HH.ru API
        location_map = {
            "москва": "1",
            "санкт-петербург": "2",
            "минск": "16",
            "киев": "115",
            "алматы": "159",
        }
        
        location_lower = location.lower()
        for key, value in location_map.items():
            if key in location_lower:
                return value
        
        return None
    
    @staticmethod
    def _experience_to_hh_format(experience: str) -> Optional[str]:
        """Преобразует уровень опыта в формат HH.ru."""
        experience_map = {
            "нет опыта": "noExperience",
            "стажер": "noExperience",
            "junior": "noExperience",
            "начальный": "noExperience",
            "1-3 года": "between1And3",
            "1-3 лет": "between1And3",
            "middle": "between1And3",
            "3-6 лет": "between3And6",
            "3-6 года": "between3And6",
            "senior": "between3And6",
            "сеньор": "between3And6",
            "более 6 лет": "moreThan6",
            "lead": "moreThan6",
            "руководитель": "moreThan6",
        }
        
        experience_lower = experience.lower()
        for key, value in experience_map.items():
            if key in experience_lower:
                return value
        
        return None
    
    @staticmethod
    def _schedule_to_hh_format(schedule: str) -> Optional[str]:
        """Преобразует график работы в формат HH.ru."""
        schedule_map = {
            "полный день": "fullDay",
            "удаленная работа": "remote",
            "удаленка": "remote",
            "гибкий график": "flexible",
            "сменный график": "shift",
            "вахтовый метод": "flyInFlyOut",
        }
        
        schedule_lower = schedule.lower()
        for key, value in schedule_map.items():
            if key in schedule_lower:
                return value
        
        return None


# ============================================
# Модели для кэширования
# ============================================

class CacheStats(BaseModel):
    """Статистика кэша."""
    hits: int = 0
    misses: int = 0
    total: int = 0
    hit_rate: float = 0.0
    size: int = 0
    avg_ttl: float = 0.0
    
    @property
    def hit_rate_percentage(self) -> float:
        """Возвращает hit rate в процентах."""
        return self.hit_rate * 100


# ============================================
# Вспомогательные функции
# ============================================

def vacancy_to_dict(vacancy: Vacancy) -> Dict[str, Any]:
    """Преобразует вакансию в словарь для сериализации."""
    return vacancy.dict(exclude_none=True)


def dict_to_vacancy(data: Dict[str, Any]) -> Vacancy:
    """Преобразует словарь в объект Vacancy."""
    return Vacancy(**data)