from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from models import Base

class RawCompetency(Base):
    __tablename__ = "raw_competencies"

    id = Column(Integer, primary_key=True)
    vacancy_id = Column(Integer, ForeignKey("vacancies.id"), nullable=False)
    text = Column(Text, nullable=False)
    processed = Column(Boolean, default=False)

    vacancy = relationship("Vacancy")

class UnknownCompetency(Base):
    __tablename__ = "unknown_competencies"

    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    source_vacancy_id = Column(Integer, ForeignKey("vacancies.id"), nullable=True)
