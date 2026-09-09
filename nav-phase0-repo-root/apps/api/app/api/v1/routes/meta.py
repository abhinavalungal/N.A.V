"""Service metadata endpoint.

The web console reads this to display the running version and to label which
providers are currently returning mock data.
"""

from fastapi import APIRouter

from app.api.dependencies import HealthServiceDep
from app.schemas.health import MetaResponse

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("", response_model=MetaResponse, summary="Service and provider metadata")
async def meta(service: HealthServiceDep) -> MetaResponse:
    return service.meta()
