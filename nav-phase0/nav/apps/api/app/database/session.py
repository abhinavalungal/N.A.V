"""Async engine and session factory.

The engine is created lazily so that importing the application never opens a
socket - important for unit tests and for `alembic` running in a container
where the database may not be up yet.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.core.errors import DependencyUnavailableError


def database_configured() -> bool:
    """Whether this instance has a database to talk to at all."""
    return get_settings().database_configured


@lru_cache
def get_engine() -> AsyncEngine:
    """Return the process-wide async engine.

    Raises rather than inventing a default: a deployment without DATABASE_URL
    should say so, not quietly dial localhost.
    """
    settings = get_settings()
    if not settings.database_url:
        raise DependencyUnavailableError(
            "DATABASE_URL is not configured; this instance has no database"
        )
    return create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
        pool_recycle=1800,
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide session factory."""
    return async_sessionmaker(
        bind=get_engine(),
        expire_on_commit=False,
        autoflush=False,
    )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a transactional session."""
    factory = get_sessionmaker()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Close all pooled connections (called on application shutdown)."""
    if not database_configured():
        return
    await get_engine().dispose()
