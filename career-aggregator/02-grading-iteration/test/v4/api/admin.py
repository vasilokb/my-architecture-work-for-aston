from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from infrastructure.database import get_session
from infrastructure.scheduler import update_grading_schedule
from repositories.joblog_repo import JobLogRepo
from schemas.admin import ScheduleUpdate, JobLogRead

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.post("/schedule")
async def update_schedule(body: ScheduleUpdate):
    update_grading_schedule(body.cron_expression, lambda: None)
    return {"updated": True}

@router.get("/jobs")
async def list_jobs(job_type: str | None = None, page: int = 1, limit: int = 50, session: Session = Depends(get_session)):
    repo = JobLogRepo(session)
    items, total = repo.get_jobs(job_type, page, limit)
    result = []
    for j in items:
        result.append({
            "id": j.id, "job_type": j.job_type,
            "started_at": str(j.started_at),
            "finished_at": str(j.finished_at) if j.finished_at else None,
            "status": j.status, "error_message": j.error_message,
        })
    return {"items": result, "total": total, "page": page, "limit": limit}

@router.get("/jobs/{id}", response_model=JobLogRead)
async def get_job(id: int, session: Session = Depends(get_session)):
    repo = JobLogRepo(session)
    j = repo.get_by_id(id)
    return JobLogRead(
        id=j.id, job_type=j.job_type, started_at=str(j.started_at),
        finished_at=str(j.finished_at) if j.finished_at else None,
        status=j.status, error_message=j.error_message,
    )
