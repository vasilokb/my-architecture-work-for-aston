# Руководство по реализации: Python модульный монолит для AI-платформы оценки пресейлов

## Цель документа

Это практическое руководство для команды стажёров, которые будут реализовывать архитектуру, описанную в `avd-python.md`. Документ содержит пошаговые инструкции, лучшие практики и конкретные технические рекомендации.

---

## 1. Подготовка окружения разработки

### 1.1. Установка базовых инструментов

```bash
# 1. Установка Python 3.11+
python --version  # Проверка версии

# 2. Установка Poetry для управления зависимостями
curl -sSL https://install.python-poetry.org | python3 -

# 3. Установка Docker и Docker Compose
# Для Windows: Docker Desktop
# Для Linux/Mac: следовать официальной документации

# 4. Установка Git
git --version
```

### 1.2. Создание структуры проекта

```bash
# Создание корневой директории проекта
mkdir presale-platform
cd presale-platform

# Инициализация Git репозитория
git init

# Инициализация Poetry проекта
poetry init
# Ответить на вопросы (можно использовать значения по умолчанию)

# Создание базовой структуры каталогов
mkdir -p app/{core,modules/{users,presales,files,processing,llm,validation,analysis,results},shared}
mkdir -p alembic/versions tests/{unit,integration} docs

# Создание основных файлов
touch app/__init__.py app/main.py
touch app/core/{__init__.py,config.py,database.py,security.py,exceptions.py}
touch app/shared/{__init__.py,models.py,schemas.py}

# Для каждого модуля
for module in users presales files processing llm validation analysis results; do
  touch app/modules/$module/{__init__.py,models.py,schemas.py,api.py,service.py}
done

# Создание конфигурационных файлов
touch docker-compose.yml Dockerfile .env.example .gitignore README.md
```

### 1.3. Настройка Poetry зависимостей

Отредактируйте `pyproject.toml`:

```toml
[tool.poetry]
name = "presale-platform"
version = "0.1.0"
description = "AI Presale Platform - Modular Monolith"
authors = ["Your Team <team@example.com>"]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
sqlalchemy = "^2.0.0"
alembic = "^1.12.0"
psycopg2-binary = "^2.9.0"
pydantic = {extras = ["email"], version = "^2.0.0"}
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
python-multipart = "^0.0.6"
boto3 = "^1.28.0"
aioboto3 = "^12.0.0"
openai = "^1.0.0"
httpx = "^0.25.0"
pypdf2 = "^3.0.0"
python-docx = "^0.8.11"
openpyxl = "^3.1.0"
jsonschema = "^4.19.0"
numpy = "^1.24.0"
pandas = "^2.0.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-cov = "^4.1.0"
factory-boy = "^3.3.0"
black = "^23.0.0"
isort = "^5.12.0"
flake8 = "^6.0.0"
mypy = "^1.5.0"
pre-commit = "^3.4.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"

[tool.black]
line-length = 88
target-version = ['py311']
```

Установите зависимости:
```bash
poetry install
```

---

## 2. Настройка базы данных и миграций

### 2.1. Конфигурация PostgreSQL в Docker Compose

`docker-compose.yml`:
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: presale
      POSTGRES_PASSWORD: presale_password
      POSTGRES_DB: presale_platform
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U presale"]
      interval: 10s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

  keycloak:
    image: quay.io/keycloak/keycloak:21.0
    environment:
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: admin
    command: start-dev
    ports:
      - "8081:8080"

volumes:
  postgres_data:
  minio_data:
```

### 2.2. Настройка SQLAlchemy и Alembic

`app/core/database.py`:
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency для получения сессии БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

`app/core/config.py`:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://presale:presale_password@localhost:5432/presale_platform"
    
    # MinIO/S3
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    
    # Keycloak
    KEYCLOAK_URL: str = "http://localhost:8081"
    KEYCLOAK_REALM: str = "presale-platform"
    KEYCLOAK_CLIENT_ID: str = "presale-client"
    
    # LLM
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()
```

Инициализация Alembic:
```bash
poetry run alembic init alembic
```

Настройка `alembic.ini` и `alembic/env.py` для работы с SQLAlchemy моделями.

---

## 3. Реализация модулей (компонентов)

### 3.1. Общий паттерн для каждого модуля

Каждый модуль должен следовать этой структуре:

```
app/modules/{module_name}/
├── __init__.py           # Экспорт публичного API модуля
├── models.py             # SQLAlchemy модели
├── schemas.py            # Pydantic схемы (DTO)
├── api.py                # FastAPI роутеры
├── service.py            # Бизнес-логика
└── dependencies.py       # Зависимости модуля (опционально)
```

### 3.2. Пример: Модуль Presales (Presale Manager)

`app/modules/presales/models.py`:
```python
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.shared.models import Base
import enum

class PresaleStatus(enum.Enum):
    DRAFT = "draft"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Presale(Base):
    __tablename__ = "presales"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1000))
    status = Column(Enum(PresaleStatus), default=PresaleStatus.DRAFT)
    created_by = Column(String(255))
    created_at = Column(DateTime, server_default="now()")
    updated_at = Column(DateTime, onupdate="now()")
    
    # Связи
    documents = relationship("Document", back_populates="presale")
    results = relationship("Result", back_populates="presale")
```

`app/modules/presales/schemas.py`:
```python
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from .models import PresaleStatus

class PresaleBase(BaseModel):
    name: str
    description: Optional[str] = None

class PresaleCreate(PresaleBase):
    pass

class PresaleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[PresaleStatus] = None

class Presale(PresaleBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    status: PresaleStatus
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None
```

`app/modules/presales/service.py`:
```python
from sqlalchemy.orm import Session
from typing import List, Optional
from . import models, schemas

class PresaleService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_presale(self, presale: schemas.PresaleCreate, user_id: str) -> models.Presale:
        db_presale = models.Presale(
            name=presale.name,
            description=presale.description,
            created_by=user_id
        )
        self.db.add(db_presale)
        self.db.commit()
        self.db.refresh(db_presale)
        return db_presale
    
    def get_presale(self, presale_id: int) -> Optional[models.Presale]:
        return self.db.query(models.Presale).filter(models.Presale.id == presale_id).first()
    
    def list_presales(self, skip: int = 0, limit: int = 100) -> List[models.Presale]:
        return self.db.query(models.Presale).offset(skip).limit(limit).all()
    
    def update_presale(self, presale_id: int, presale_update: schemas.PresaleUpdate) -> Optional[models.Presale]:
        db_presale = self.get_presale(presale_id)
        if not db_presale:
            return None
        
        update_data = presale_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_presale, field, value)
        
        self.db.commit()
        self.db.refresh(db_presale)
        return db_presale
```

`app/modules/presales/api.py`:
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from . import schemas, service

router = APIRouter(prefix="/presales", tags=["presales"])

@router.post("/", response_model=schemas.Presale)
def create_presale(
    presale: schemas.PresaleCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    presale_service = service.PresaleService(db)
    return presale_service.create_presale(presale, current_user)

@router.get("/", response_model=List[schemas.Presale])
def list_presales(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    presale_service = service.PresaleService(db)
    return presale_service.list_presales(skip, limit)

@router.get("/{presale_id}", response_model=schemas.Presale)
def get_presale(
    presale_id: int,
    db: Session = Depends(get_db)
):
    presale_service = service.PresaleService(db)
    presale = presale_service.get_presale(presale_id)
    if not presale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Presale not found"
        )
    return presale
```

### 3.3. Регистрация модулей в основном приложении

`app/main.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.modules import presales, users, files, processing, llm, validation, analysis, results

app = FastAPI(
    title="AI Presale Platform",
    description="Modular monolith for AI-powered presale estimation",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Регистрация роутеров модулей
app.include_router(presales.api.router)
app.include_router(users.api.router)
app.include_router(files.api.router)
app.include_router(processing.api.router)
app.include_router(llm.api.router)
app.include_router(validation.api.router)
app.include_router(analysis.api.router)
app.include_router(results.api.router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

---

## 4. Критические компоненты: детальная реализация

### 4.1. Queue Manager на PostgreSQL SKIP LOCKED

`app/modules/processing/models.py` (часть):
```python
from sqlalchemy import Column, Integer, String, DateTime, Enum, JSON, Boolean
import enum

class TaskStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ProcessingTask(Base):
    __tablename__ = "processing_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    version = Column(Integer, nullable=False)
    mode = Column(String(50))  # "alternative" или "reestimate"
    payload = Column(JSON)  # Table 1 для reestimate
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    next_attempt_at = Column(DateTime)
    locked_at = Column(DateTime)
    locked_by = Column(String(255))
    created_at = Column(DateTime, server_default="now()")
```

`app/modules/processing/service.py` (часть):
```python
from sqlalchemy import select, update
from sqlalchemy.orm import Session
import datetime

class QueueService:
    def __init__(self, db: Session):
        self.db = db
    
    def enqueue_task(self, task_data: dict) -> models.ProcessingTask:
        task = models.ProcessingTask(**task_data)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task
    
    def dequeue_task(self, worker_id: str) -> Optional[models.ProcessingTask]:
        # Использование SKIP LOCKED для конкурентного извлечения задач
        stmt = (
            select(models.ProcessingTask)
            .where(
                models.ProcessingTask.status == models.TaskStatus.PENDING,
                models.ProcessingTask.next_attempt_at <= datetime.datetime.now()
            )
            .order_by(models.ProcessingTask.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        
        task = self.db.execute(stmt).scalar_one_or_none()
        
        if task:
            task.status = models.TaskStatus.PROCESSING
            task.locked_at = datetime.datetime.now()
            task.locked_by = worker_id
            self.db.commit()
        
        return task
    
    def complete_task(self, task_id: int, result: dict):
        task = self.db.get(models.ProcessingTask, task_id)
        if task:
            task.status = models.TaskStatus.COMPLETED
            task.locked_at = None
            task.locked_by = None
            self.db.commit()
    
    def fail_task(self, task_id: int, error: