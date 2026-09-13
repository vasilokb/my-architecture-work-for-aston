from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from models import Base

class CompetencyCategory(Base):
    __tablename__ = "competency_categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)

    competencies = relationship("Competency", secondary="competency_category_link", back_populates="categories")

class Competency(Base):
    __tablename__ = "competencies"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)

    categories = relationship("CompetencyCategory", secondary="competency_category_link", back_populates="competencies")
    variants = relationship("CompetencyVariant", back_populates="competency")
    requirements = relationship("ParsedRequirement", back_populates="competency")

class CompetencyVariant(Base):
    __tablename__ = "competency_variants"

    id = Column(Integer, primary_key=True)
    competency_id = Column(Integer, ForeignKey("competencies.id"), nullable=False)
    variant_name = Column(String(255), nullable=False)

    competency = relationship("Competency", back_populates="variants")

class CategoryLink(Base):
    __tablename__ = "competency_category_link"

    competency_id = Column(Integer, ForeignKey("competencies.id"), primary_key=True)
    category_id = Column(Integer, ForeignKey("competency_categories.id"), primary_key=True)
