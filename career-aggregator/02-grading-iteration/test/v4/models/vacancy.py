from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from models import Base

class Vacancy(Base):
    __tablename__ = "vacancies"

    id = Column(Integer, primary_key=True)
    hh_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(500), nullable=False)
    requirement = Column(Text, default="")
    responsibility = Column(Text, default="")
    employer_name = Column(String(500), default="")
    city = Column(String(200), default="")
    salary_from = Column(Integer, nullable=True)
    salary_to = Column(Integer, nullable=True)
    salary_currency = Column(String(10), nullable=True)
    url = Column(String(500), nullable=True)

    parsed = relationship("ParsedVacancy", back_populates="vacancy")
