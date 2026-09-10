"""Liveness and readiness checks.

Each dependency is probed for real. If a probe fails the component is reported
DOWN with the reason - it is never assumed healthy and never silently omitted.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy import text

from app.config import Settings
from app.database.session import get_engine
from app.schemas.health import (
    ComponentHealth,
    ComponentStatus,
    LivenessResponse,
    MetaResponse,
    ReadinessResponse,
)

logger = logging.getLogger("nav.health")

PROBE_TIMEOUT_SECONDS = 3.0
CURRENT_PHASE = "Phase 0 - foundation"


class HealthService:
    """Probes the dependencies this instance needs in order to serve traffic."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def liveness(self) -> LivenessResponse:
        """Process-level liveness. Must not touch any dependency."""
        return LivenessResponse(
            service=self._settings.app_name,
            version=self._settings.app_version,
            environment=self._settings.app_env,
            timestamp=datetime.now(UTC),
        )

    async def readiness(self) -> ReadinessResponse:
        """Probe every required dependency concurrently."""
        database, redis = await asyncio.gather(self._check_database(), self._check_redis())
        components = [database, redis]
        # A deliberately unconfigured dependency is not a fault; only a
        # dependency that failed to answer blocks readiness.
        return ReadinessResponse(
            ready=all(component.status is not ComponentStatus.DOWN for component in components),
            service=self._settings.app_name,
            version=self._settings.app_version,
            environment=self._settings.app_env,
            timestamp=datetime.now(UTC),
            components=components,
        )

    def meta(self) -> MetaResponse:
        """Build metadata plus which providers are currently mocked."""
        return MetaResponse(
            name=self._settings.app_name,
            full_name=self._settings.app_full_name,
            version=self._settings.app_version,
            environment=self._settings.app_env,
            phase=CURRENT_PHASE,
            api_version=self._settings.api_v1_prefix,
            mock_providers=self._settings.mock_providers,
            llm_provider=self._settings.llm_provider,
            weather_provider=self._settings.weather_provider,
            routing_provider=self._settings.routing_provider,
        )

    async def _check_database(self) -> ComponentHealth:
        if not self._settings.database_url:
            return ComponentHealth(
                name="postgres",
                status=ComponentStatus.NOT_CONFIGURED,
                detail="DATABASE_URL is unset; required from Phase 1",
            )

        started = time.perf_counter()
        try:
            async with asyncio.timeout(PROBE_TIMEOUT_SECONDS):
                engine = get_engine()
                async with engine.connect() as connection:
                    await connection.execute(text("SELECT 1"))
        except TimeoutError:
            return ComponentHealth(
                name="postgres",
                status=ComponentStatus.DOWN,
                detail=f"probe timed out after {PROBE_TIMEOUT_SECONDS:g}s",
            )
        except Exception as exc:
            logger.warning("database probe failed", extra={"error_type": type(exc).__name__})
            return ComponentHealth(
                name="postgres",
                status=ComponentStatus.DOWN,
                detail=type(exc).__name__,
            )
        return ComponentHealth(
            name="postgres",
            status=ComponentStatus.UP,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )

    async def _check_redis(self) -> ComponentHealth:
        if not self._settings.redis_url:
            return ComponentHealth(
                name="redis",
                status=ComponentStatus.NOT_CONFIGURED,
                detail="REDIS_URL is unset; required from Phase 4",
            )

        started = time.perf_counter()
        client: Redis | None = None
        try:
            async with asyncio.timeout(PROBE_TIMEOUT_SECONDS):
                client = Redis.from_url(self._settings.redis_url)
                await client.ping()
        except TimeoutError:
            return ComponentHealth(
                name="redis",
                status=ComponentStatus.DOWN,
                detail=f"probe timed out after {PROBE_TIMEOUT_SECONDS:g}s",
            )
        except Exception as exc:
            logger.warning("redis probe failed", extra={"error_type": type(exc).__name__})
            return ComponentHealth(
                name="redis", status=ComponentStatus.DOWN, detail=type(exc).__name__
            )
        finally:
            if client is not None:
                await client.aclose()
        return ComponentHealth(
            name="redis",
            status=ComponentStatus.UP,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )
