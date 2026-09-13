from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from infrastructure.database import get_session
from infrastructure.llm_factory import create_provider
from product.dictionary_service import DictionaryService
from product.grading_service import grade_vacancies
from schemas.grading import GradingRunRequest, GradingStatus

router = APIRouter(prefix="/api/grading", tags=["grading"])

_tasks: dict[str, dict] = {}

@router.post("/run")
async def run_grading(body: GradingRunRequest, session: Session = Depends(get_session)):
    import uuid, asyncio
    task_id = f"grd-{uuid.uuid4().hex[:8]}"
    _tasks[task_id] = {"task_id": task_id, "status": "running", "processed": 0, "failed": 0, "total": body.limit}
    asyncio.create_task(_run(task_id, body.provider, body.limit, session))
    return GradingStatus(**_tasks[task_id])

async def _run(task_id: str, provider_name: str, limit: int, session: Session):
    try:
        provider = create_provider(provider_name)
        dictionary = DictionaryService(session)
        result = await grade_vacancies(session, provider, dictionary, limit)
        _tasks[task_id].update(result)
        _tasks[task_id]["status"] = "completed"
    except Exception as e:
        _tasks[task_id]["status"] = "failed"
        _tasks[task_id]["error"] = str(e)

@router.get("/status/{task_id}")
async def grading_status(task_id: str):
    return _tasks.get(task_id, {"error": "task not found"})
