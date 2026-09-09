# Deployment

## Local

    cp .env.example .env
    # set JWT_SECRET, e.g. openssl rand -hex 32
    docker compose up --build

Then:

    http://localhost:3000        console
    http://localhost:8000/docs   API documentation
    http://localhost:8000/health liveness
    http://localhost:8000/ready  readiness

`docker compose up` is enough. No API key, no external service, no network
access to a third party is required: providers default to mock and the fonts
are self-hosted.

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

## Production

See `infrastructure/aws/README.md` for the target topology. Two rules carry
over: the worker scales independently of the API so optimisation load never
touches request latency, and `/health` backs the load-balancer target group
while `/ready` gates deployment cutover.
