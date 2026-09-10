# Docker assets

- `postgres/init/` - SQL run once when the Postgres volume is first created.
  Extensions only; tables come from Alembic.
- `./Dockerfile` at the repository root builds the API and the Celery worker -
  one image, two commands. It lives at the root because that is the path every
  deployment platform looks for by default.
- `apps/web/Dockerfile` builds the console. It also builds from the root
  context, which it needs in order to resolve the npm workspace.
- `docker-compose.yml` at the root wires everything together.

Rebuild a single service:

    docker compose build api
    docker compose up -d api

Reset the database completely (destroys data):

    docker compose down -v
