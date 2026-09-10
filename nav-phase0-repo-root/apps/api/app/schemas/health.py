"""Health, readiness and service metadata schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ComponentStatus(StrEnum):
    """Status of a single dependency.

    NOT_CONFIGURED means the deployment deliberately runs without it - not a
    fault, so it does not block readiness. UNKNOWN means the probe could not
    run at all. A dependency is never reported UP unless it actually answered.
    """

    UP = "UP"
    DOWN = "DOWN"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    UNKNOWN = "UNKNOWN"


class ComponentHealth(BaseModel):
    """Result of probing one dependency."""

    name: str
    status: ComponentStatus
    latency_ms: float | None = Field(
        default=None, description="Round-trip time of the probe; null if it never ran."
    )
    detail: str | None = Field(
        default=None, description="Short reason when the component is not UP."
    )


class LivenessResponse(BaseModel):
    """Answer to 'is the process alive?' - deliberately dependency-free."""

    status: str = "ok"
    service: str
    version: str
    environment: str
    timestamp: datetime


class ReadinessResponse(BaseModel):
    """Answer to 'can this instance serve traffic?'"""

    ready: bool
    service: str
    version: str
    environment: str
    timestamp: datetime
    components: list[ComponentHealth]


class MetaResponse(BaseModel):
    """Build and provider metadata, used by the web console."""

    name: str
    full_name: str
    version: str
    environment: str
    phase: str
    api_version: str
    mock_providers: list[str] = Field(
        description="Providers currently returning mock data. Shown in the UI as mock."
    )
    llm_provider: str
    weather_provider: str
    routing_provider: str
