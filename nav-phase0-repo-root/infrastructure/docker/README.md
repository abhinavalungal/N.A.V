# Docker assets

- `postgres/init/` - SQL run once when the Postgres volume is first created.
  Extensions only; tables come from Alembic.
- Service Dockerfiles live beside the code they build: `apps/api/Dockerfile`
  and `apps/web/Dockerfile`. `docker-compose.yml` at the repository root wires
  them together.

Rebuild a single service:

    docker compose build api
    docker compose up -d api

Reset the database completely (destroys data):

    docker compose down -v
