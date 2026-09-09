"""Container-level health endpoints, mounted at the root (not under /api/v1).

`/health` answers whether the process is alive - orchestrators use it to decide
whether to restart the container, so it must not depend on Postgres or Redis.
`/ready` answers whether this instance can serve traffic and returns 503 when a
required dependency is down.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.dependencies import HealthServiceDep
from app.schemas.health import LivenessResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=LivenessResponse, summary="Liveness probe")
async def health(service: HealthServiceDep) -> LivenessResponse:
    return service.liveness()


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    responses={503: {"model": ReadinessResponse, "description": "A dependency is down"}},
)
async def ready(service: HealthServiceDep, response: Response) -> ReadinessResponse:
    report = await service.readiness()
    if not report.ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return report
