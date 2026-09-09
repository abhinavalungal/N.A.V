"""Celery wiring. The task runs in-process; no broker is contacted."""

from __future__ import annotations

from app.workers.celery_app import celery_app, ping


def test_ping_task_is_registered() -> None:
    assert "nav.ping" in celery_app.tasks


def test_ping_returns_a_result() -> None:
    result = ping()

    assert result["pong"] is True
    assert result["timestamp"]


def test_broker_comes_from_configuration() -> None:
    assert celery_app.conf.broker_url.startswith("redis://")
    assert celery_app.conf.timezone == "UTC"
