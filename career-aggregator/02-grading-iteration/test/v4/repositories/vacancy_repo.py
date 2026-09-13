from sqlalchemy import or_
from sqlalchemy.orm import Session
from models.vacancy import Vacancy
from exceptions import NotFoundError

class VacancyRepo:
    def __init__(self, session: Session):
        self.session = session

    def get_all_raw(self, page: int = 1, limit: int = 50, q: str | None = None) -> tuple[list[Vacancy], int]:
        query = self.session.query(Vacancy)
        if q:
            ql = q.lower()
            query = query.filter(
                or_(Vacancy.name.ilike(f"%{ql}%"), Vacancy.requirement.ilike(f"%{ql}%"))
            )
        total = query.count()
        items = query.order_by(Vacancy.id.desc()).offset((page - 1) * limit).limit(limit).all()
        return items, total

    def get_by_id(self, vacancy_id: int) -> Vacancy:
        v = self.session.get(Vacancy, vacancy_id)
        if not v:
            raise NotFoundError("Vacancy", vacancy_id)
        return v

    def get_by_hh_id(self, hh_id: str) -> Vacancy | None:
        return self.session.query(Vacancy).filter(Vacancy.hh_id == hh_id).first()

    def create(self, hh_id: str, name: str, requirement: str = "", responsibility: str = "",
               employer_name: str = "", city: str = "", salary_from: int | None = None,
               salary_to: int | None = None, salary_currency: str | None = None, url: str | None = None) -> Vacancy:
        v = Vacancy(hh_id=hh_id, name=name, requirement=requirement, responsibility=responsibility,
                    employer_name=employer_name, city=city, salary_from=salary_from,
                    salary_to=salary_to, salary_currency=salary_currency, url=url)
        self.session.add(v)
        self.session.flush()
        return v

    def delete(self, vacancy_id: int):
        v = self.get_by_id(vacancy_id)
        self.session.delete(v)
        self.session.flush()

    def count_ungraded(self) -> int:
        from models.parsed import ParsedVacancy
        return self.session.query(Vacancy).outerjoin(
            ParsedVacancy, Vacancy.id == ParsedVacancy.vacancy_id
        ).filter(ParsedVacancy.id.isnone()).count()
