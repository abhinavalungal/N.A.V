# Architecture

N.A.V. is not an LLM with some APIs bolted on. It is a data platform with
deterministic maritime calculations, an optimiser, an approval workflow and an
audit trail. The language model is one component inside that system, and it is
the component least trusted with numbers.

## The rule that shapes everything

The LLM understands intent, plans, selects tools, orchestrates and explains.
It never calculates fuel, ETA, distance, emissions or a regulatory figure.
Those come from deterministic services, and the explanation the operator reads
is generated from the values those services returned.

```
User
 |
 v
N.A.V. agent  ---- plans, selects tools, explains
 |
 v
Agent orchestrator  ---- enforces tool limits, permissions, timeouts
 |
 v
Tool registry  ---- validated, authorised, logged
 |
 +-- External providers (weather, routing, prices)
 +-- Internal services (fuel, ETA, emissions)
 |
 v
Deterministic calculation
 |
 v
Optimisation
 |
 v
Recommendation  ---- traceable to inputs and model versions
 |
 v
Human approval
 |
 v
Action -> Outcome -> Feedback loop
```

## Layering

Request handling runs one direction only:

    API route -> Service -> Repository -> Database

Route handlers validate and delegate; they hold no business logic. Services own
the domain rules. Repositories own the queries and enforce company scoping.
Nothing skips a layer, which is what keeps tenant isolation checkable in one
place rather than scattered across handlers.

Providers (LLM, weather, routing) sit behind interfaces. The application
depends on the interface, never on a vendor, so swapping Ollama for a hosted
model, or the mock weather source for a real one, is a configuration change.

## Processes

| Process  | Responsibility                                              |
| -------- | ----------------------------------------------------------- |
| `api`    | HTTP, validation, orchestration, migrations on start         |
| `worker` | Celery: optimisation runs, ingestion, scheduled monitoring   |
| `web`    | Next.js console, server-rendered against the API             |

Optimisation is expensive and never blocks a request: the API queues a run and
returns an id, and the worker moves it through `QUEUED -> RUNNING ->
CALCULATING -> VALIDATING -> COMPLETED`.

## Data honesty

Every externally sourced value carries its source, timestamp and quality
status (`FRESH`, `STALE`, `MISSING`, `ESTIMATED`, `MOCK`, `INVALID`,
`UNAVAILABLE`). A provider failure produces `UNAVAILABLE`, never a plausible
substitute, and the agent says which data it is missing rather than working
around the gap. The console labels mock providers wherever it shows them.

## What exists today (Phase 0)

Built: application shells for API, worker and web; configuration; structured
logging with request correlation; error handling; database and cache wiring;
Alembic baseline; health and readiness probes; service metadata endpoint;
Docker stack; CI.

Not built: authentication, any domain table, any provider implementation, the
optimiser, the agent, the tool registry, approvals, audit. Directories exist
for these with a note naming the phase that fills them - they are empty on
purpose rather than filled with scaffolding that does nothing.

See `deployment.md` for how it runs and `security.md` for the trust
boundaries.
