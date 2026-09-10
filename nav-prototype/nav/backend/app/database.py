"""SQLAlchemy setup. SQLite by default, Postgres if DATABASE_URL points at one.

Local development and the demo run on a single SQLite file with no migrations.
Hosted deployments usually have an ephemeral filesystem, so DATABASE_URL can be
pointed at Postgres instead:

    DATABASE_URL=postgresql+psycopg://user:password@host/dbname

Nothing else in the application changes. The SQLite-only connection arguments
and pragmas below are applied only when the engine really is SQLite.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


def engine_kwargs(database_url: str) -> dict:
    """Connection settings that differ between SQLite and a network database."""
    if make_url(database_url).get_backend_name() == "sqlite":
        # FastAPI serves requests from a thread pool; SQLite connections would
        # otherwise refuse to cross threads.
        return {"connect_args": {"check_same_thread": False}}
    # Hosted Postgres drops idle connections. Test one before handing it out,
    # and recycle well inside the usual idle timeout.
    return {"pool_pre_ping": True, "pool_recycle": 280}


IS_SQLITE = make_url(settings.database_url).get_backend_name() == "sqlite"

engine = create_engine(
    settings.database_url, future=True, **engine_kwargs(settings.database_url)
)


if IS_SQLITE:

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _record):  # pragma: no cover - driver glue
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    """FastAPI dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401  (register mappers)

    Base.metadata.create_all(bind=engine)
