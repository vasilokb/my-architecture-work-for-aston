from sqlalchemy.orm import Session
from models.raw import RawCompetency
from exceptions import NotFoundError

class RawRepo:
    def __init__(self, session: Session):
        self.session = session

    def get_unprocessed(self) -> list[RawCompetency]:
        return self.session.query(RawCompetency).filter(RawCompetency.processed == False).all()

    def mark_processed(self, ids: list[int]):
        self.session.query(RawCompetency).filter(RawCompetency.id.in_(ids)).update(
            {RawCompetency.processed: True}, synchronize_session="fetch"
        )

    def create(self, vacancy_id: int, text: str) -> RawCompetency:
        r = RawCompetency(vacancy_id=vacancy_id, text=text)
        self.session.add(r)
        self.session.flush()
        return r

    def get_by_id(self, raw_id: int) -> RawCompetency:
        r = self.session.get(RawCompetency, raw_id)
        if not r:
            raise NotFoundError("RawCompetency", raw_id)
        return r
