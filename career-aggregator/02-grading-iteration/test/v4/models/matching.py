from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from models import Base

class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(500), default="")
    description = Column(Text, default="")

    user = relationship("User", back_populates="profiles")

class MatchingResult(Base):
    __tablename__ = "matching_results"

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("candidate_profiles.id"), nullable=False)
    parsed_vacancy_id = Column(Integer, ForeignKey("parsed_vacancies.id"), nullable=False)
    match_score = Column(Float, default=0.0)
