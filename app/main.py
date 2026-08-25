from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api import auth, care, moods, privacy, reminders
from app.api.errors import http_exception_handler, validation_exception_handler
from app.core.config import get_settings
from app.database import Base, SessionLocal, engine
from app import models  # noqa: F401 - registers SQLAlchemy models

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    yield


settings = get_settings()
app = FastAPI(
    title="CareGuard QA API",
    version="1.0.0",
    description=(
        "适老化情绪关怀平台。情绪结果仅用于日常关怀，不构成医疗诊断或治疗建议。"
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))[:64]
    request.state.request_id = request_id
    started = perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = f"{(perf_counter() - started) * 1000:.2f}"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; "
        "img-src 'self' data:; connect-src 'self'"
    )
    return response


@app.get("/health", tags=["Operations"])
def health() -> dict:
    return {"status": "ok", "service": settings.app_name, "version": "1.0.0"}


@app.get("/health/ready", tags=["Operations"])
def readiness() -> dict:
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ready", "database": "connected"}


for router in (auth.router, care.router, moods.router, reminders.router, privacy.router):
    app.include_router(router, prefix=settings.api_prefix)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def web_app() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
