from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from models.parsed import ParsedVacancy, ParsedRequirement
from models.competency import Competency
from exceptions import NotFoundError

class ParsedRepo:
    def __init__(self, session: Session):
        self.session = session

    def get_graded(self, page: int = 1, limit: int = 50, q: str | None = None, level: str | None = None) -> tuple[list[ParsedVacancy], int]:
        query = self.session.query(ParsedVacancy)
        if q:
            ql = q.lower()
            query = query.filter(ParsedVacancy.job_title.ilike(f"%{ql}%"))
        if level:
            query = query.filter(ParsedVacancy.overall_level == level)
        total = query.count()
        items = query.order_by(ParsedVacancy.id.desc()).offset((page - 1) * limit).limit(limit).all()
        return items, total

    def get_by_id(self, parsed_id: int) -> ParsedVacancy:
        pv = self.session.get(ParsedVacancy, parsed_id)
        if not pv:
            raise NotFoundError("ParsedVacancy", parsed_id)
        return pv

    def get_skills(self, parsed_id: int) -> list[ParsedRequirement]:
        pv = self.get_by_id(parsed_id)
        return self.session.query(ParsedRequirement).options(
            joinedload(ParsedRequirement.competency)
        ).filter(ParsedRequirement.parsed_vacancy_id == parsed_id).all()

    def save_result(self, parsed_vacancy: ParsedVacancy, requirements: list[ParsedRequirement]):
        self.session.add(parsed_vacancy)
        self.session.flush()
        for req in requirements:
            req.parsed_vacancy_id = parsed_vacancy.id
            self.session.add(req)
        self.session.flush()

    def is_processed(self, vacancy_id: int) -> bool:
        return self.session.query(ParsedVacancy).filter(
            ParsedVacancy.vacancy_id == vacancy_id
        ).first() is not None
