"""Celery application.

Redis is both broker and result backend. Optimisation runs move onto this
worker in Phase 4; for now it carries a single ping task so the service in
docker-compose is genuinely functional rather than decorative.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from celery import Celery

from app.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

celery_app = Celery(
    "nav",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
)


@celery_app.task(name="nav.ping")
def ping() -> dict[str, Any]:
    """Round-trip check that the broker and worker are wired up."""
    return {
        "pong": True,
        "worker": "nav",
        "version": settings.app_version,
        "timestamp": datetime.now(UTC).isoformat(),
    }
