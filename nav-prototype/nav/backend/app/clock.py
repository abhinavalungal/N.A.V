"""One source of truth for "now" in the backend: naive UTC datetimes."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Current UTC time as a naive datetime, matching how SQLite stores it."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
