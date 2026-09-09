# N.A.V. — Nautical Agentic Navigator

Intelligence for Every Voyage.

An agentic maritime operations platform: vessel and voyage data, deterministic
maritime calculations, an optimisation engine, an AI agent that plans and
explains, and a human who approves before anything happens.

**Current state: Phase 0 — foundation.** The stack runs, the services talk to
each other, and the console reports real status. There are no vessels, no
voyages, no optimiser and no agent yet. The left rail in the console marks
every planned screen with the phase that will build it, and nothing pretends
to work that does not.

## Run it

    cp .env.example .env
    # set JWT_SECRET — openssl rand -hex 32
    docker compose up --build

| URL                            | What                        |
| ------------------------------ | --------------------------- |
| http://localhost:3000          | Console                     |
| http://localhost:8000/docs     | API documentation           |
| http://localhost:8000/health   | Liveness                    |
| http://localhost:8000/ready    | Readiness, with per-component detail |

No API key and no external service is needed. Every provider defaults to mock,
and mocked data is labelled as mock wherever it is shown.

## Layout

    apps/api          FastAPI backend and Celery worker
    apps/web          Next.js console
    packages/         shared-types — one definition of the API contract
    optimization/     deterministic maritime maths (Phases 3–4)
    data/             seed and mock fixtures
    infrastructure/   Docker assets, AWS topology
    docs/             architecture, database, API, security, deployment, …
    tests/            end-to-end suite (Phase 7)

## Working on it

    make up          start the stack
    make down        stop it
    make reset       stop it and delete all data
    make test        backend tests
    make lint        ruff, mypy, eslint, tsc
    make check       everything CI runs
    make migrate     apply migrations in the running api container

Outside Docker:

    cd apps/api && pip install -e ".[dev]" && uvicorn app.main:app --reload
    npm install && npm run dev --workspace=@nav/web

## The rule that shapes the codebase

The language model plans, selects tools and explains. It does not calculate
fuel, ETA, distance, emissions or any regulatory figure — those come from
deterministic services, and an explanation may only contain numbers those
services produced. When data is unavailable, N.A.V. says so instead of
substituting something plausible.

Read `docs/architecture.md` next.
