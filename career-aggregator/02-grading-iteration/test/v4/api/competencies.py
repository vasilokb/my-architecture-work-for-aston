from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from infrastructure.database import get_session
from repositories.competency_repo import CompetencyRepo
from schemas.competency import (
    CategoryRead, CategoryCreate, CategoryUpdate,
    CompetencyRead, CompetencyCreate, CompetencyUpdate,
    VariantRead, VariantCreate, VariantUpdate,
)

router = APIRouter(prefix="/api", tags=["competencies"])

def _to_category(cat) -> CategoryRead:
    return CategoryRead(id=cat.id, name=cat.name)

def _to_competency(comp) -> CompetencyRead:
    return CompetencyRead(
        id=comp.id, name=comp.name,
        categories=[_to_category(c) for c in comp.categories],
        variants=[v.variant_name for v in comp.variants],
    )

@router.get("/competency-categories", response_model=list[CategoryRead])
async def get_categories(session: Session = Depends(get_session)):
    repo = CompetencyRepo(session)
    return [_to_category(c) for c in repo.get_categories()]

@router.post("/competency-categories", response_model=CategoryRead, status_code=201)
async def create_category(body: CategoryCreate, session: Session = Depends(get_session)):
    repo = CompetencyRepo(session)
    cat = repo.create_category(body.name)
    session.commit()
    return _to_category(cat)

@router.put("/competency-categories/{id}", response_model=CategoryRead)
async def update_category(id: int, body: CategoryUpdate, session: Session = Depends(get_session)):
    repo = CompetencyRepo(session)
    cat = repo.update_category(id, body.name)
    session.commit()
    return _to_category(cat)

@router.delete("/competency-categories/{id}")
async def delete_category(id: int, session: Session = Depends(get_session)):
    repo = CompetencyRepo(session)
    repo.delete_category(id)
    session.commit()
    return {"deleted": True}

@router.get("/competencies", response_model=list[CompetencyRead])
async def get_competencies(category_id: int | None = None, q: str | None = None, session: Session = Depends(get_session)):
    repo = CompetencyRepo(session)
    return [_to_competency(c) for c in repo.get_competencies(category_id=category_id, q=q)]

@router.get("/competencies/{id}", response_model=CompetencyRead)
async def get_competency(id: int, session: Session = Depends(get_session)):
    repo = CompetencyRepo(session)
    return _to_competency(repo.get_competency(id))

@router.post("/competencies", response_model=CompetencyRead, status_code=201)
async def create_competency(body: CompetencyCreate, session: Session = Depends(get_session)):
    repo = CompetencyRepo(session)
    comp = repo.create_competency(body.name, body.category_ids)
    session.commit()
    return _to_competency(comp)

@router.put("/competencies/{id}", response_model=CompetencyRead)
async def update_competency(id: int, body: CompetencyUpdate, session: Session = Depends(get_session)):
    repo = CompetencyRepo(session)
    comp = repo.update_competency(id, body.name, body.category_ids)
    session.commit()
    return _to_competency(comp)

@router.delete("/competencies/{id}")
async def delete_competency(id: int, session: Session = Depends(get_session)):
    repo = CompetencyRepo(session)
    repo.delete_competency(id)
    session.commit()
    return {"deleted": True}

@router.get("/competencies/{id}/variants", response_model=list[VariantRead])
async def get_variants(id: int, session: Session = Depends(get_session)):
    repo = CompetencyRepo(session)
    comp = repo.get_competency(id)
    return [VariantRead(id=v.id, competency_id=v.competency_id, variant_name=v.variant_name) for v in comp.variants]

@router.post("/competencies/{id}/variants", response_model=VariantRead, status_code=201)
async def add_variant(id: int, body: VariantCreate, session: Session = Depends(get_session)):
    repo = CompetencyRepo(session)
    v = repo.add_variant(id, body.variant_name)
    session.commit()
    return VariantRead(id=v.id, competency_id=v.competency_id, variant_name=v.variant_name)

@router.put("/competencies/{id}/variants/{vid}", response_model=VariantRead)
async def update_variant(id: int, vid: int, body: VariantUpdate, session: Session = Depends(get_session)):
    repo = CompetencyRepo(session)
    v = repo.update_variant(vid, body.variant_name)
    session.commit()
    return VariantRead(id=v.id, competency_id=v.competency_id, variant_name=v.variant_name)

@router.delete("/competencies/{id}/variants/{vid}")
async def delete_variant(id: int, vid: int, session: Session = Depends(get_session)):
    repo = CompetencyRepo(session)
    repo.delete_variant(vid)
    session.commit()
    return {"deleted": True}
