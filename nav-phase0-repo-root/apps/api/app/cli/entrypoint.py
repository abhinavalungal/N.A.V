"""Container entry point: wait for the database, migrate, then hand over.

This lives inside the application package rather than in a loose shell script
next to the Dockerfile. A script file has to be committed with the right
executable bit and LF line endings or the container fails at start; a module
inside `app/` is copied with the rest of the code, is linted and type-checked
with it, and behaves identically on every platform.

Migrations run in the API container only. `RUN_MIGRATIONS=0` on the worker
keeps two processes from racing for the same lock.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from app.config import get_settings
from app.core.logging import configure_logging

logger = logging.getLogger("nav.entrypoint")

WAIT_ATTEMPTS = 30
WAIT_SECONDS = 2.0


def alembic_ini() -> Path:
    """Locate alembic.ini whether the package runs from the source tree or an
    installed copy."""
    candidates = [
        Path(__file__).resolve().parents[2] / "alembic.ini",
        Path.cwd() / "alembic.ini",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise SystemExit("alembic.ini not found in " + ", ".join(str(c) for c in candidates))


def should_run_migrations(environ: dict[str, str] | None = None) -> bool:
    """Migrations run unless RUN_MIGRATIONS is explicitly switched off."""
    env = os.environ if environ is None else environ
    return env.get("RUN_MIGRATIONS", "1") not in {"0", "false", "False"}


def to_asyncpg_dsn(database_url: str) -> str:
    """Strip the SQLAlchemy driver marker; asyncpg.connect wants a plain DSN."""
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def _wait_for_database(dsn: str) -> None:
    """Block until Postgres accepts a connection, or give up loudly."""
    import asyncpg

    for attempt in range(1, WAIT_ATTEMPTS + 1):
        try:
            connection = await asyncpg.connect(dsn)
        except Exception as exc:  # noqa: BLE001 - any failure means "not yet"
            logger.info(
                "database not ready",
                extra={"attempt": attempt, "error_type": type(exc).__name__},
            )
            await asyncio.sleep(WAIT_SECONDS)
        else:
            await connection.close()
            logger.info("database ready", extra={"attempt": attempt})
            return

    raise SystemExit(
        f"database did not accept a connection after "
        f"{WAIT_ATTEMPTS} attempts over {int(WAIT_ATTEMPTS * WAIT_SECONDS)}s"
    )


def _run_migrations() -> None:
    """Apply migrations through Alembic's Python API."""
    from alembic import command
    from alembic.config import Config

    ini = alembic_ini()
    logger.info("applying migrations", extra={"config": str(ini)})
    config = Config(str(ini))
    config.set_main_option("script_location", str(ini.parent / "migrations"))
    command.upgrade(config, "head")
    logger.info("migrations applied")


def main(argv: list[str] | None = None) -> None:
    """Prepare the environment, then replace this process with the real command."""
    args = sys.argv[1:] if argv is None else argv
    settings = get_settings()
    configure_logging(settings.log_level)

    if should_run_migrations():
        asyncio.run(_wait_for_database(to_asyncpg_dsn(settings.database_url)))
        _run_migrations()
    else:
        logger.info("skipping migrations", extra={"reason": "RUN_MIGRATIONS is off"})

    if not args:
        raise SystemExit("no command given to run")

    logger.info("starting", extra={"command": args})
    os.execvp(args[0], args)  # noqa: S606 - argv comes from the image CMD


if __name__ == "__main__":
    main()
