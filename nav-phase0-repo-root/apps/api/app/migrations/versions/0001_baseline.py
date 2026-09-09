"""Baseline revision.

Establishes the alembic_version table so later phases have a common ancestor.
No domain tables exist yet - the Postgres extensions themselves are created by
infrastructure/docker/postgres/init/00-extensions.sql before the app connects.

Revision ID: 0001
Revises:
Create Date: 2026-09-09
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Nothing to apply: this revision only marks the schema baseline."""


def downgrade() -> None:
    """Nothing to revert."""
