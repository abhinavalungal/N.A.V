"""FastAPI application factory.

Layering rule (docs/architecture.md): API -> Service -> Repository -> Database.
Route handlers contain no business logic.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1 import api_router
from app.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from app.database.session import dispose_engine

DESCRIPTION = """
N.A.V. (Nautical Agentic Navigator) - maritime agentic operations platform.

Deterministic services own every number. The LLM plans, selects tools and
explains results; it never performs fuel, ETA, emissions or optimisation
calculations.
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start-up and shutdown hooks."""
    settings = get_settings()
    logging.getLogger("nav").info(
        "api starting",
        extra={
            "version": settings.app_version,
            "environment": settings.app_env,
            "mock_providers": settings.mock_providers,
        },
    )
    yield
    await dispose_engine()
    logging.getLogger("nav").info("api stopped")


def create_app() -> FastAPI:
    """Build and configure the ASGI application."""
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=f"{settings.app_name} - {settings.app_full_name}",
        description=DESCRIPTION,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
