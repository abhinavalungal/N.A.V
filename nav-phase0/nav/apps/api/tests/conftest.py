"""Shared pytest fixtures.

The suite runs entirely offline: no Postgres, no Redis, no network. Dependency
probes are either overridden or pointed at a closed port on purpose.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://nav:nav@127.0.0.1:5499/nav_test")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6399/0")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")


@pytest.fixture
def settings():  # type: ignore[no-untyped-def]
    from app.config import get_settings

    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
def app(settings):  # type: ignore[no-untyped-def]
    from app.main import create_app

    return create_app()


@pytest.fixture
async def client(app) -> AsyncIterator[AsyncClient]:  # type: ignore[no-untyped-def]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client


@pytest.fixture(autouse=True)
def _reset_engine_cache() -> Iterator[None]:
    from app.database.session import get_engine, get_sessionmaker

    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
    yield
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
