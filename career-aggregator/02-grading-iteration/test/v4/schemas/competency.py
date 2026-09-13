from pydantic import BaseModel

class CategoryRead(BaseModel):
    id: int
    name: str

class CategoryCreate(BaseModel):
    name: str

class CategoryUpdate(BaseModel):
    name: str

class VariantRead(BaseModel):
    id: int
    competency_id: int
    variant_name: str

class VariantCreate(BaseModel):
    variant_name: str

class VariantUpdate(BaseModel):
    variant_name: str

class CompetencyRead(BaseModel):
    id: int
    name: str
    categories: list[CategoryRead]
    variants: list[str]

class CompetencyCreate(BaseModel):
    name: str
    category_ids: list[int]

class CompetencyUpdate(BaseModel):
    name: str | None = None
    category_ids: list[int] | None = None
