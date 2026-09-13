from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from infrastructure.database import get_session
from repositories.vacancy_repo import VacancyRepo
from repositories.parsed_repo import ParsedRepo
from schemas.vacancy import (
    VacancyExtractRequest, ExtractStatus,
    VacancyRawRead, VacancyRawDetail,
    VacancyGradedRead, SkillRead,
)

router = APIRouter(prefix="/api/vacancies", tags=["vacancies"])

_tasks: dict[str, dict] = {}

@router.post("/extract")
async def extract(body: VacancyExtractRequest):
    import uuid
    task_id = f"ext-{uuid.uuid4().hex[:8]}"
    _tasks[task_id] = {"task_id": task_id, "status": "running", "loaded": 0, "failed": 0, "total": body.pages * 50}
    import asyncio
    asyncio.create_task(_run_extract(task_id, body.query, body.pages))
    return ExtractStatus(**_tasks[task_id])

async def _run_extract(task_id: str, query: str, pages: int):
    import requests
    from infrastructure.database import SessionLocal
    session = SessionLocal()
    try:
        repo = VacancyRepo(session)
        loaded = 0
        failed = 0
        for page in range(pages):
            try:
                r = requests.get("https://api.hh.ru/vacancies", params={"text": query, "page": page, "per_page": 50}, timeout=30)
                if r.status_code != 200:
                    failed += 1
                    continue
                items = r.json().get("items", [])
                for item in items:
                    try:
                        snippet = item.get("snippet", {})
                        repo.create(
                            hh_id=str(item["id"]), name=item.get("name", ""),
                            requirement=snippet.get("requirement", "") or "",
                            responsibility=snippet.get("responsibility", "") or "",
                            employer_name=item.get("employer", {}).get("name", "") or "",
                            city=item.get("area", {}).get("name", "") or "",
                            salary_from=item.get("salary", {}).get("from"),
                            salary_to=item.get("salary", {}).get("to"),
                            salary_currency=item.get("salary", {}).get("currency"),
                            url=item.get("alternate_url"),
                        )
                        loaded += 1
                    except Exception:
                        failed += 1
                _tasks[task_id]["loaded"] = loaded
                _tasks[task_id]["failed"] = failed
                session.commit()
            except Exception:
                failed += 1
                session.rollback()
        _tasks[task_id]["status"] = "completed"
    finally:
        session.close()

@router.get("/extract/status/{task_id}")
async def extract_status(task_id: str):
    return _tasks.get(task_id, {"error": "task not found"})

@router.get("/raw")
async def get_raw(page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200), q: str | None = None, session: Session = Depends(get_session)):
    repo = VacancyRepo(session)
    items, total = repo.get_all_raw(page=page, limit=limit, q=q)
    parsed_repo = ParsedRepo(session)
    result = []
    for v in items:
        result.append(VacancyRawRead(
            id=v.id, hh_id=v.hh_id, name=v.name, employer=v.employer_name, city=v.city,
            salary_from=v.salary_from, salary_to=v.salary_to, salary_currency=v.salary_currency,
            url=v.url, graded=parsed_repo.is_processed(v.id),
        ))
    return {"items": result, "total": total, "page": page, "limit": limit}

@router.get("/raw/{id}")
async def get_raw_detail(id: int, session: Session = Depends(get_session)):
    repo = VacancyRepo(session)
    v = repo.get_by_id(id)
    return VacancyRawDetail(
        id=v.id, hh_id=v.hh_id, name=v.name, requirement=v.requirement, responsibility=v.responsibility,
        employer=v.employer_name, city=v.city, salary_from=v.salary_from, salary_to=v.salary_to,
        salary_currency=v.salary_currency, url=v.url,
    )

@router.delete("/raw/{id}")
async def delete_raw(id: int, session: Session = Depends(get_session)):
    repo = VacancyRepo(session)
    repo.delete(id)
    session.commit()
    return {"deleted": True}

@router.get("/graded")
async def get_graded(page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200), q: str | None = None, level: str | None = None, session: Session = Depends(get_session)):
    repo = ParsedRepo(session)
    items, total = repo.get_graded(page=page, limit=limit, q=q, level=level)
    result = []
    for pv in items:
        skills = repo.get_skills(pv.id)
        result.append(VacancyGradedRead(
            id=pv.id, hh_id=pv.vacancy.hh_id, title=pv.job_title, level=pv.overall_level,
            salary_from=pv.salary_min, salary_to=pv.salary_max, salary_currency=pv.currency,
            skills_count=len(skills), url=pv.url,
        ))
    return {"items": result, "total": total, "page": page, "limit": limit}

@router.get("/graded/{id}")
async def get_graded_detail(id: int, session: Session = Depends(get_session)):
    repo = ParsedRepo(session)
    pv = repo.get_by_id(id)
    return {
        "id": pv.id, "hh_id": pv.vacancy.hh_id, "title": pv.job_title, "level": pv.overall_level,
        "salary_from": pv.salary_min, "salary_to": pv.salary_max, "salary_currency": pv.currency,
        "requirement": pv.requirement_raw, "responsibility": pv.responsibility_raw, "url": pv.url,
    }

@router.get("/graded/{id}/skills", response_model=list[SkillRead])
async def get_skills(id: int, session: Session = Depends(get_session)):
    repo = ParsedRepo(session)
    skills = repo.get_skills(id)
    return [SkillRead(
        competency_id=s.competency_id, name=s.competency.name, level=s.required_level,
        mandatory=s.is_mandatory, confidence=s.confidence, evidence=s.evidence,
    ) for s in skills]
