"""N.A.V. backend entrypoint.

    uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from .ai.provider import get_ai_provider
from .api import agent, analytics, fuel, optimization, vessels, voyages, weather
from .config import PROJECT_DIR, settings
from .database import init_db
from .schemas import Meta
from .services import weather as weather_service
from .services.emissions import UnknownFuelType

VERSION = "1.0.0"

# If the frontend has been exported (cd frontend && npm run build), this one
# service serves the whole application: no second process, no CORS, one URL.
FRONTEND_DIR = Path(
    os.getenv("NAV_FRONTEND_DIR", str(PROJECT_DIR / "frontend" / "out"))
).resolve()
SERVE_FRONTEND = (FRONTEND_DIR / "index.html").is_file()

logger = logging.getLogger("nav")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    logger.info(
        "N.A.V. ready - AI provider: %s, weather provider: %s",
        get_ai_provider().name,
        weather_service.get_provider().name,
    )
    if SERVE_FRONTEND:
        logger.info("Serving the exported frontend from %s", FRONTEND_DIR)
    else:
        logger.info(
            "No frontend build at %s - running API only. Build it with: "
            "cd frontend && npm run build",
            FRONTEND_DIR,
        )
    yield


app = FastAPI(
    title=settings.app_name,
    version=VERSION,
    description="Intelligence for Every Voyage. Prototype maritime voyage optimization API.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (vessels, voyages, weather, fuel, optimization, agent, analytics):
    app.include_router(router.router, prefix=settings.api_prefix)


@app.get("/", tags=["meta"], include_in_schema=not SERVE_FRONTEND)
def root():
    """The exported app when one is present, otherwise a pointer to the docs."""
    if SERVE_FRONTEND:
        return FileResponse(FRONTEND_DIR / "index.html")
    return {"name": "N.A.V.", "tagline": "Intelligence for Every Voyage.", "docs": "/docs"}


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


@app.get(f"{settings.api_prefix}/meta", response_model=Meta, tags=["meta"])
def meta():
    provider = get_ai_provider()
    return Meta(
        app="N.A.V.",
        version=VERSION,
        ai_provider=provider.name,
        ai_model=provider.model,
        weather_provider=weather_service.get_provider().name,
        database=settings.database_url.split("/")[-1],
    )


# --- error handling: useful messages, never a stack trace ------------------


@app.exception_handler(HTTPException)
def http_error(_request: Request, exc: HTTPException):
    titles = {400: "Invalid request", 404: "Not found", 409: "Conflict"}
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": titles.get(exc.status_code, "Request failed"), "detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
def validation_error(_request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first.get("loc", [])[1:]) or "request"
    return JSONResponse(
        status_code=422,
        content={"error": "Invalid request", "detail": f"{field}: {first.get('msg', 'invalid')}"},
    )


@app.exception_handler(ValueError)
def value_error(_request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"error": "Invalid input", "detail": str(exc)})


@app.exception_handler(UnknownFuelType)
def fuel_type_error(_request: Request, exc: UnknownFuelType):
    return JSONResponse(status_code=400, content={"error": "Unknown fuel type", "detail": str(exc)})


@app.exception_handler(SQLAlchemyError)
def database_error(_request: Request, exc: SQLAlchemyError):
    logger.exception("Database error", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Database error",
            "detail": "The database rejected that operation. Check the backend log.",
        },
    )


@app.exception_handler(Exception)
def unhandled_error(_request: Request, exc: Exception):
    logger.exception("Unhandled error", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal error", "detail": "Something went wrong. Check the backend log."},
    )


# --- static frontend -------------------------------------------------------
# Mounted last: every API route is already registered, so this only ever
# catches paths the API does not own.
if SERVE_FRONTEND:
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
