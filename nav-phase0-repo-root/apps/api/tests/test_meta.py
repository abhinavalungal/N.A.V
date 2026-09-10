"""Service metadata endpoint - mock providers must be declared, not hidden."""

from __future__ import annotations

from httpx import AsyncClient


async def test_meta_reports_version_and_mock_providers(client: AsyncClient) -> None:
    response = await client.get("/api/v1/meta")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "N.A.V."
    assert body["full_name"] == "Nautical Agentic Navigator"
    assert body["api_version"] == "/api/v1"
    assert set(body["mock_providers"]) == {"llm", "weather", "routing"}


async def test_openapi_schema_is_served(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/health" in paths
    assert "/ready" in paths
    assert "/api/v1/meta" in paths
