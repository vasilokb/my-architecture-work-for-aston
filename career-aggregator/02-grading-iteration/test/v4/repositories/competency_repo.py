from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from models.competency import Competency, CompetencyCategory, CompetencyVariant, CategoryLink
from exceptions import NotFoundError

class CompetencyRepo:
    def __init__(self, session: Session):
        self.session = session

    def get_categories(self) -> list[CompetencyCategory]:
        return self.session.query(CompetencyCategory).order_by(CompetencyCategory.name).all()

    def create_category(self, name: str) -> CompetencyCategory:
        cat = CompetencyCategory(name=name)
        self.session.add(cat)
        self.session.flush()
        return cat

    def update_category(self, cat_id: int, name: str) -> CompetencyCategory:
        cat = self.session.get(CompetencyCategory, cat_id)
        if not cat:
            raise NotFoundError("CompetencyCategory", cat_id)
        cat.name = name
        self.session.flush()
        return cat

    def delete_category(self, cat_id: int):
        cat = self.session.get(CompetencyCategory, cat_id)
        if cat:
            self.session.delete(cat)
            self.session.flush()

    def get_competencies(self, category_id: int | None = None, q: str | None = None) -> list[Competency]:
        query = self.session.query(Competency).options(
            joinedload(Competency.categories),
            joinedload(Competency.variants),
        )
        if category_id:
            query = query.join(Competency.categories).filter(CompetencyCategory.id == category_id)
        if q:
            ql = q.lower()
            query = query.filter(
                or_(
                    Competency.name.ilike(f"%{ql}%"),
                    CompetencyVariant.variant_name.ilike(f"%{ql}%"),
                )
            ).distinct()
        return query.order_by(Competency.name).all()

    def get_competency(self, comp_id: int) -> Competency:
        comp = self.session.query(Competency).options(
            joinedload(Competency.categories),
            joinedload(Competency.variants),
        ).get(comp_id)
        if not comp:
            raise NotFoundError("Competency", comp_id)
        return comp

    def create_competency(self, name: str, category_ids: list[int]) -> Competency:
        comp = Competency(name=name)
        for cid in category_ids:
            cat = self.session.get(CompetencyCategory, cid)
            if cat:
                comp.categories.append(cat)
        self.session.add(comp)
        self.session.flush()
        return comp

    def update_competency(self, comp_id: int, name: str | None = None, category_ids: list[int] | None = None) -> Competency:
        comp = self.get_competency(comp_id)
        if name is not None:
            comp.name = name
        if category_ids is not None:
            comp.categories.clear()
            for cid in category_ids:
                cat = self.session.get(CompetencyCategory, cid)
                if cat:
                    comp.categories.append(cat)
        self.session.flush()
        return comp

    def delete_competency(self, comp_id: int):
        comp = self.session.get(Competency, comp_id)
        if comp:
            self.session.delete(comp)
            self.session.flush()

    def add_variant(self, comp_id: int, variant_name: str) -> CompetencyVariant:
        comp = self.get_competency(comp_id)
        v = CompetencyVariant(competency_id=comp_id, variant_name=variant_name)
        self.session.add(v)
        self.session.flush()
        return v

    def update_variant(self, variant_id: int, variant_name: str) -> CompetencyVariant:
        v = self.session.get(CompetencyVariant, variant_id)
        if not v:
            raise NotFoundError("CompetencyVariant", variant_id)
        v.variant_name = variant_name
        self.session.flush()
        return v

    def delete_variant(self, variant_id: int):
        v = self.session.get(CompetencyVariant, variant_id)
        if v:
            self.session.delete(v)
            self.session.flush()
