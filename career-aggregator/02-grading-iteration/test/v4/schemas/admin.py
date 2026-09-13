from pydantic import BaseModel

class ScheduleUpdate(BaseModel):
    cron_expression: str

class JobLogRead(BaseModel):
    id: int
    job_type: str
    started_at: str
    finished_at: str | None = None
    status: str
    error_message: str | None = None
