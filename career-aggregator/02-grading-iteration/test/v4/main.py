from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
from api import auth, competencies, vacancies, grading, admin
from infrastructure.database import engine
from infrastructure.scheduler import start_scheduler, stop_scheduler
from models import Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    start_scheduler()
    yield
    stop_scheduler()

app = FastAPI(title="Career Aggregator API", version="0.1.0", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(competencies.router)
app.include_router(vacancies.router)
app.include_router(grading.router)
app.include_router(admin.router)

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_, exc):
    from fastapi.responses import JSONResponse
    from fastapi import status
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=422, content={"detail": str(exc)})

@app.get("/health")
async def health():
    return {"status": "ok"}
