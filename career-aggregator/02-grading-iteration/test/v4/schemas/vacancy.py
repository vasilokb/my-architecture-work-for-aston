from pydantic import BaseModel

class VacancyExtractRequest(BaseModel):
    query: str
    pages: int = 20

class ExtractStatus(BaseModel):
    task_id: str
    status: str
    loaded: int = 0
    failed: int = 0
    total: int = 0

class VacancyRawRead(BaseModel):
    id: int
    hh_id: str
    name: str
    employer: str
    city: str
    salary_from: int | None = None
    salary_to: int | None = None
    salary_currency: str | None = None
    url: str | None = None
    graded: bool = False

class VacancyRawDetail(BaseModel):
    id: int
    hh_id: str
    name: str
    requirement: str
    responsibility: str
    employer: str
    city: str
    salary_from: int | None = None
    salary_to: int | None = None
    salary_currency: str | None = None
    url: str | None = None

class VacancyGradedRead(BaseModel):
    id: int
    hh_id: str
    title: str
    level: str
    salary_from: int | None = None
    salary_to: int | None = None
    salary_currency: str | None = None
    skills_count: int
    url: str | None = None

class SkillRead(BaseModel):
    competency_id: int
    name: str
    level: str
    mandatory: bool
    confidence: float
    evidence: str
