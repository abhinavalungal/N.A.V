"""Readiness reporting.

A dependency is only ever reported UP when it actually answered; when it does
not, the endpoint says so and returns 503 instead of degrading silently.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_health_service
from app.schemas.health import ComponentHealth, ComponentStatus, ReadinessResponse
from app.services.health_service import HealthService


class _StubHealthService(HealthService):
    def __init__(self, components: list[ComponentHealth]) -> None:
        self._components = components

    async def readiness(self) -> ReadinessResponse:
        return ReadinessResponse(
            ready=all(c.status is ComponentStatus.UP for c in self._components),
            service="N.A.V.",
            version="0.1.0",
            environment="test",
            timestamp=datetime.now(UTC),
            components=self._components,
        )


async def _client_with(app, components: list[ComponentHealth]) -> AsyncClient:  # type: ignore[no-untyped-def]
    app.dependency_overrides[get_health_service] = lambda: _StubHealthService(components)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


async def test_ready_when_all_components_up(app) -> None:  # type: ignore[no-untyped-def]
    components = [
        ComponentHealth(name="postgres", status=ComponentStatus.UP, latency_ms=1.2),
        ComponentHealth(name="redis", status=ComponentStatus.UP, latency_ms=0.4),
    ]
    async with await _client_with(app, components) as client:
        response = await client.get("/ready")

    assert response.status_code == 200
    assert response.json()["ready"] is True


async def test_not_ready_returns_503_and_names_the_failure(app) -> None:  # type: ignore[no-untyped-def]
    components = [
        ComponentHealth(name="postgres", status=ComponentStatus.UP, latency_ms=1.2),
        ComponentHealth(name="redis", status=ComponentStatus.DOWN, detail="ConnectionError"),
    ]
    async with await _client_with(app, components) as client:
        response = await client.get("/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["ready"] is False
    redis = next(c for c in body["components"] if c["name"] == "redis")
    assert redis["status"] == "DOWN"
    assert redis["detail"] == "ConnectionError"


@pytest.mark.parametrize("component_name", ["postgres", "redis"])
async def test_unreachable_dependency_is_reported_down(settings, component_name: str) -> None:  # type: ignore[no-untyped-def]
    """The real probes point at closed ports here, so both must report DOWN."""
    report = await HealthService(settings).readiness()

    component = next(c for c in report.components if c.name == component_name)
    assert component.status is ComponentStatus.DOWN
    assert component.detail
    assert component.latency_ms is None
    assert report.ready is False
