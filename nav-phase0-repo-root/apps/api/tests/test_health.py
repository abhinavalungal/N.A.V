"""Liveness endpoint and HTTP plumbing."""

from __future__ import annotations

from httpx import AsyncClient


async def test_health_returns_ok_without_touching_dependencies(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "N.A.V."
    assert body["environment"] == "test"
    assert body["version"]
    assert body["timestamp"]


async def test_response_carries_request_id(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.headers["X-Request-ID"]


async def test_supplied_request_id_is_echoed(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"X-Request-ID": "voyage-42"})

    assert response.headers["X-Request-ID"] == "voyage-42"


async def test_security_headers_are_applied(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


async def test_unknown_route_returns_json_404(client: AsyncClient) -> None:
    response = await client.get("/no-such-route")

    assert response.status_code == 404
