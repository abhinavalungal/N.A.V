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

| Service    | Image / build          | Port | Notes                              |
| ---------- | ---------------------- | ---- | ---------------------------------- |
| `postgres` | pgvector/pgvector:pg16 | 5432 | init SQL creates `pgcrypto`, `vector` |
| `redis`    | redis:7-alpine         | 6379 | append-only persistence on         |
| `api`      | `./Dockerfile`         | 8000 | migrates on start, then uvicorn    |
| `worker`   | `./Dockerfile`         | -    | Celery, `RUN_MIGRATIONS=0`         |
| `web`      | `apps/web/Dockerfile`  | 3000 | Next.js standalone output          |

`api` and `worker` share one image and differ only in command. Both Dockerfiles
build from the repository root: the API's sits at the root because that is
where every platform looks by default, and the console's needs the root anyway
to resolve the npm workspace.

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

Neither datastore is required. Unset, they are reported `NOT_CONFIGURED` and
the service is ready. Set but unreachable, they are reported `DOWN` and it is
not - a URL that points at nothing is a fault, an absent URL is a choice.

## Render

`render.yaml` at the repository root defines the deployment. Render looks for
`./Dockerfile` at the root by default and this repo has one per service, so
each service names its own `dockerfilePath` and `dockerContext`.

Dashboard -> New -> Blueprint -> select the repo. Three free resources come
up: the API, the console and Postgres. One value is prompted for -
`API_INTERNAL_URL` on `nav-web`, the API's URL. It does not exist until the
first deploy, so deploy once, copy the URL from the dashboard, set it, and
redeploy.

No database and no cache are provisioned. `DATABASE_URL` and `REDIS_URL` stay
unset, readiness reports both as `NOT_CONFIGURED`, the entrypoint skips
migrations because there is nothing to migrate, and the service is ready
anyway. Phase 1 needs Postgres and Phase 4 needs Redis; `render.yaml` carries
both, commented, with the wiring ready to uncomment. Note that Render has no
free plan for background workers, so the Celery service costs money from
Phase 4.

Setting the same thing up by hand instead of through the Blueprint:

| Service | Dockerfile path       | Docker context |
| ------- | --------------------- | -------------- |
| api     | `./Dockerfile`        | `.` - both are Render's defaults, so change nothing |
| web     | `apps/web/Dockerfile` | `.` |

A Blueprint only drives services created through **New -> Blueprint**. A
service created through **New -> Web Service** ignores `render.yaml` entirely
and keeps whatever its dashboard settings say - which is why the API's
Dockerfile is at the root: that path needs no dashboard setting at all.

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

A different message - `failed to read dockerfile: open Dockerfile: no such
file or directory` - means the platform looked for `./Dockerfile` and the
repository root does not have one. Either the project sits inside a wrapper
folder in the repo (check `git ls-files | head`; the paths should start with
`apps/`, not `nav/apps/`), or `render.yaml` is not at the root, or the service
was not created from the Blueprint.

Start-up needs no shell script: `python -m app.cli.entrypoint` waits for
Postgres, applies migrations unless `RUN_MIGRATIONS=0`, then execs the
container command. It ships inside the package, so there is no separate file to
commit, chmod, or keep free of CRLF line endings.

## When the API starts but cannot reach Postgres

    database not ready  attempt 1  target dpg-abc:5432/nav  error ...

The log names the host it is dialling and the driver's own message. Read that
message rather than the error class:

- `Name or service not known` - the hostname does not resolve. On Render this
  usually means the database is in a different region from the service; the
  private network does not cross regions.
- `Connection refused` - the host resolves but nothing is listening. Check the
  port, and that the database has finished provisioning.
- `target localhost:5432` on a deployed service - `DATABASE_URL` is not set,
  so the default is being used. The log warns about this explicitly.

The container exits after 30 attempts over 60 seconds rather than sitting in a
loop pretending to start.

## AWS

See `infrastructure/aws/README.md` for the target topology. Two rules carry
over: the worker scales independently of the API so optimisation load never
touches request latency, and `/health` backs the load-balancer target group
while `/ready` gates deployment cutover.
