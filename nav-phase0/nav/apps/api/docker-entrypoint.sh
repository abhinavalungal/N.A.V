#!/bin/sh
# Wait for Postgres, apply migrations, then hand over to the container command.
# Only the API container migrates; RUN_MIGRATIONS=0 on the worker keeps two
# processes from racing for the same lock.
set -e

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  echo "waiting for database"
  python - <<'PY'
import asyncio
import os
import sys

import asyncpg

url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")


async def wait() -> None:
    for attempt in range(1, 31):
        try:
            connection = await asyncpg.connect(url)
            await connection.close()
            return
        except Exception as exc:  # noqa: BLE001 - retry regardless of cause
            print(f"attempt {attempt}: {type(exc).__name__}", flush=True)
            await asyncio.sleep(2)
    sys.exit("database did not become available")


asyncio.run(wait())
PY
  echo "applying migrations"
  alembic upgrade head
fi

exec "$@"
