"""The API root, which is the URL a person opens in a browser."""

from __future__ import annotations

from httpx import AsyncClient


async def test_root_serves_a_page_rather_than_a_404(client: AsyncClient) -> None:
    response = await client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


async def test_page_links_to_every_endpoint_that_exists(client: AsyncClient) -> None:
    body = (await client.get("/")).text

    for path in ("/docs", "/health", "/ready", "/api/v1/meta"):
        assert f'href="{path}"' in body


async def test_page_declares_the_phase_and_mocked_providers(client: AsyncClient) -> None:
    """The prototype must not look more finished than it is."""
    body = (await client.get("/")).text

    assert "Phase 0" in body
    assert "mock" in body


async def test_page_needs_no_external_resource(client: AsyncClient) -> None:
    """It has to render with no internet, so nothing may be fetched remotely."""
    body = (await client.get("/")).text

    assert "http://" not in body
    assert "https://" not in body


async def test_favicon_answers_instead_of_404ing(client: AsyncClient) -> None:
    response = await client.get("/favicon.ico")

    assert response.status_code == 204
