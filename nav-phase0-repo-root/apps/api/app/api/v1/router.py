"""Aggregate router for /api/v1.

Resource routers (vessels, voyages, optimizations, agent, ...) are registered
here as each phase lands.
"""

from fastapi import APIRouter

from app.api.v1.routes import meta

api_router = APIRouter()
api_router.include_router(meta.router)
