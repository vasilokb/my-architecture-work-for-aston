from sqlalchemy import Column, Integer, String, Text, Boolean, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from models import Base

class ParsedVacancy(Base):
    __tablename__ = "parsed_vacancies"

    id = Column(Integer, primary_key=True)
    vacancy_id = Column(Integer, ForeignKey("vacancies.id"), nullable=False)
    overall_level = Column(String(20), default="middle")
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    currency = Column(String(10), nullable=True)
    is_remote = Column(Boolean, default=False)
    requirement_raw = Column(Text, default="")
    responsibility_raw = Column(Text, default="")
    url = Column(String(500), nullable=True)
    status = Column(String(20), default="completed")
    processed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    vacancy = relationship("Vacancy", back_populates="parsed")
    requirements = relationship("ParsedRequirement", back_populates="parsed_vacancy")

class ParsedRequirement(Base):
    __tablename__ = "parsed_requirements"

    id = Column(Integer, primary_key=True)
    parsed_vacancy_id = Column(Integer, ForeignKey("parsed_vacancies.id"), nullable=False)
    competency_id = Column(Integer, ForeignKey("competencies.id"), nullable=False)
    required_level = Column(String(20), default="middle")
    is_mandatory = Column(Boolean, default=True)
    confidence = Column(Float, default=1.0)
    evidence = Column(Text, default="")

    parsed_vacancy = relationship("ParsedVacancy", back_populates="requirements")
    competency = relationship("Competency", back_populates="requirements")
