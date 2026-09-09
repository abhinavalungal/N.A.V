# Deployment

## Local

    docker compose up --build

Then:

    http://localhost:3000        console
    http://localhost:8000/docs   API documentation
    http://localhost:8000/health liveness
    http://localhost:8000/ready  readiness

`docker compose up` is enough - there is no `.env` to create, no key to
generate and no third party to reach: every value has a default, providers
default to mock, and the fonts are self-hosted.

## Services

| Service    | Image / build      | Port | Notes                              |
| ---------- | ------------------ | ---- | ---------------------------------- |
| `postgres` | pgvector/pgvector:pg16 | 5432 | init SQL creates `pgcrypto`, `vector` |
| `redis`    | redis:7-alpine     | 6379 | append-only persistence on         |
| `api`      | `apps/api`         | 8000 | migrates on start, then uvicorn    |
| `worker`   | `apps/api`         | -    | Celery, `RUN_MIGRATIONS=0`         |
| `web`      | `apps/web`         | 3000 | Next.js standalone output          |

`api` and `worker` share one image and differ only in command. `web` builds
from the repository root so the npm workspace resolves.

Start-up order is enforced by health checks: the API waits for Postgres and
Redis to report healthy, the worker waits for the API, and the console waits
for the API.

## Running without Docker

    cd apps/api
    pip install -e ".[dev]"
    alembic upgrade head
    uvicorn app.main:app --reload

    npm install
    npm run dev --workspace=@nav/web

Postgres and Redis still need to be reachable at the URLs in `.env`. With
neither running, the API starts and `/health` answers 200 while `/ready`
reports both as `DOWN` - which is the correct behaviour, not a failure.

## Render

`render.yaml` at the repository root defines the deployment. Render looks for
`./Dockerfile` at the root by default and this repo has one per service, so
each service names its own `dockerfilePath` and `dockerContext`.

Dashboard -> New -> Blueprint -> select the repo. Three free resources come
up: the API, the console and Postgres. One value is prompted for -
`API_INTERNAL_URL` on `nav-web`, the API's URL. It does not exist until the
first deploy, so deploy once, copy the URL from the dashboard, set it, and
redeploy.

No cache is provisioned. `REDIS_URL` stays unset, readiness reports redis as
`NOT_CONFIGURED`, and the service is ready anyway. Phase 4 is when that
changes - and Render has no free plan for background workers, so the Celery
service costs money from that point.

Setting the same thing up by hand instead of through the Blueprint:

| Service | Dockerfile path          | Docker context |
| ------- | ------------------------ | -------------- |
| api     | `apps/api/Dockerfile`    | `apps/api`     |
| web     | `apps/web/Dockerfile`    | `.` (repo root, for the npm workspace) |

What the free tier does and does not give you, as of September 2026: web
services sleep after 15 minutes idle and take around a minute to wake; the
whole workspace shares 750 instance hours a month, and two always-on services
exceed that; Postgres is capped at 1 GB and is deleted 30 days after creation;
Key Value is 25 MB and in-memory, so it does not survive a restart; and
background workers have no free plan at all. The Celery worker is therefore
commented out in `render.yaml` - Phase 0 queues no work, so nothing is lost
until Phase 4. Check Render's current pricing before relying on any of this.

Two details the platform forces:

- Render supplies `DATABASE_URL` as `postgresql://`. `Settings` rewrites it to
  `postgresql+asyncpg://` and translates libpq's `sslmode` to asyncpg's `ssl`,
  so the managed connection string works unedited.
- Render injects `PORT`. The API image's `CMD` reads it and falls back to 8000
  locally; the Next.js standalone server already honours it.

`infrastructure/docker/postgres/init/00-extensions.sql` does not run against a
managed database. Nothing in Phase 0 needs those extensions, but before Phase 9
run `CREATE EXTENSION IF NOT EXISTS vector;` against the Render database once.

## When a build fails on a COPY

    failed to compute cache key: "/<file>": not found

The build context is fine - Docker found the files copied before it. That line
means the named file is not in the repository. Check with `git ls-files`, and
`git add -f` it if a local ignore rule swallowed it.

Start-up needs no shell script: `python -m app.cli.entrypoint` waits for
Postgres, applies migrations unless `RUN_MIGRATIONS=0`, then execs the
container command. It ships inside the package, so there is no separate file to
commit, chmod, or keep free of CRLF line endings.

## AWS

See `infrastructure/aws/README.md` for the target topology. Two rules carry
over: the worker scales independently of the API so optimisation load never
touches request latency, and `/health` backs the load-balancer target group
while `/ready` gates deployment cutover.
