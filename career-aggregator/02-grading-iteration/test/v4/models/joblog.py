from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime, timezone
from models import Base

class JobLog(Base):
    __tablename__ = "job_logs"

    id = Column(Integer, primary_key=True)
    job_type = Column(String(50), nullable=False)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="running")
    error_message = Column(Text, nullable=True)
