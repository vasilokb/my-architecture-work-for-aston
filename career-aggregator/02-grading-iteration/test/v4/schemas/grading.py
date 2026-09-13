from pydantic import BaseModel

class GradingRunRequest(BaseModel):
    provider: str = "perplexity"
    limit: int = 100

class GradingStatus(BaseModel):
    task_id: str
    status: str
    processed: int = 0
    failed: int = 0
    total: int = 0
