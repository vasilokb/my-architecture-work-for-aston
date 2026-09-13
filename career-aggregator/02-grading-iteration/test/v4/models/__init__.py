from sqlalchemy.orm import declarative_base

Base = declarative_base()

from models.user import User
from models.competency import CompetencyCategory, Competency, CompetencyVariant, CategoryLink
from models.vacancy import Vacancy
from models.raw import RawCompetency, UnknownCompetency
from models.parsed import ParsedVacancy, ParsedRequirement
from models.matching import CandidateProfile, MatchingResult
from models.joblog import JobLog
