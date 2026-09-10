"""Container entry point behaviour.

Nothing here contacts a database: the pieces that would are separated from the
pieces that decide what to do.
"""

from __future__ import annotations

import pytest

from app.cli.entrypoint import (
    alembic_ini,
    database_target,
    looks_unconfigured,
    main,
    migrations_dir,
    should_run_migrations,
    to_asyncpg_dsn,
)


def test_migrations_run_by_default() -> None:
    assert should_run_migrations({}) is True


@pytest.mark.parametrize("value", ["0", "false", "False"])
def test_migrations_can_be_switched_off(value: str) -> None:
    """The worker sets this so it cannot race the API for the migration lock."""
    assert should_run_migrations({"RUN_MIGRATIONS": value}) is False


def test_driver_marker_is_stripped_for_asyncpg() -> None:
    dsn = to_asyncpg_dsn("postgresql+asyncpg://nav:nav@db:5432/nav")

    assert dsn == "postgresql://nav:nav@db:5432/nav"


def test_plain_dsn_is_left_alone() -> None:
    assert to_asyncpg_dsn("postgresql://nav:nav@db/nav") == "postgresql://nav:nav@db/nav"


def test_alembic_config_is_found() -> None:
    assert alembic_ini().is_file()


def test_missing_command_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RUN_MIGRATIONS", "0")

    with pytest.raises(SystemExit, match="no command"):
        main([])


def test_migration_scripts_are_found_inside_the_package() -> None:
    """They ship with the code, so a checkout cannot lose them separately."""
    scripts = migrations_dir()

    assert (scripts / "env.py").is_file()
    assert (scripts / "versions" / "0001_baseline.py").is_file()
    assert scripts.parent.name == "app"


def test_target_is_loggable_without_credentials() -> None:
    """The log line names the host without leaking the password."""
    target = database_target("postgresql+asyncpg://nav:s3cret@dpg-abc.render.com:5432/navdb")

    assert target == "dpg-abc.render.com:5432/navdb"
    assert "s3cret" not in target


def test_target_defaults_the_port() -> None:
    assert database_target("postgresql://nav:pw@db/nav") == "db:5432/nav"


def test_deployed_service_pointing_at_localhost_is_flagged() -> None:
    """Almost always means DATABASE_URL was never set on the service."""
    url = "postgresql+asyncpg://nav:nav@localhost:5432/nav"

    assert looks_unconfigured(url, "production") is True
    assert looks_unconfigured(url, "local") is False


def test_real_host_is_not_flagged() -> None:
    url = "postgresql+asyncpg://nav:pw@dpg-abc.render.com/nav"

    assert looks_unconfigured(url, "production") is False
