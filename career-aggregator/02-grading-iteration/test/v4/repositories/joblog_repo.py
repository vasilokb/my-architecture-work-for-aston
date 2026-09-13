from sqlalchemy.orm import Session
from models.joblog import JobLog
from exceptions import NotFoundError
from datetime import datetime, timezone

class JobLogRepo:
    def __init__(self, session: Session):
        self.session = session

    def create_job(self, job_type: str) -> JobLog:
        j = JobLog(job_type=job_type)
        self.session.add(j)
        self.session.flush()
        return j

    def update_status(self, job_id: int, status: str, error_message: str | None = None):
        j = self.get_by_id(job_id)
        j.status = status
        j.error_message = error_message
        if status in ("completed", "failed"):
            j.finished_at = datetime.now(timezone.utc)
        self.session.flush()

    def get_by_id(self, job_id: int) -> JobLog:
        j = self.session.get(JobLog, job_id)
        if not j:
            raise NotFoundError("JobLog", job_id)
        return j

    def get_jobs(self, job_type: str | None = None, page: int = 1, limit: int = 50) -> tuple[list[JobLog], int]:
        query = self.session.query(JobLog)
        if job_type:
            query = query.filter(JobLog.job_type == job_type)
        total = query.count()
        items = query.order_by(JobLog.id.desc()).offset((page - 1) * limit).limit(limit).all()
        return items, total
