# API

REST, versioned under `/api/v1`. OpenAPI is served at `/openapi.json` with
Swagger UI at `/docs` and ReDoc at `/redoc`.

## Conventions

- JSON in, JSON out. Request bodies and responses are Pydantic models.
- Errors share one shape, so the console never guesses:

      {
        "error": {
          "code": "DEPENDENCY_UNAVAILABLE",
          "message": "...",
          "details": {},
          "request_id": "..."
        }
      }

- Every response carries `X-Request-ID`. Send one and it is echoed back;
  send none and one is generated. The same id appears on every log line for
  that request.
- Expensive work returns an id and a status rather than blocking.

## Implemented

| Method | Path           | Purpose                                       |
| ------ | -------------- | --------------------------------------------- |
| GET    | `/health`      | Liveness. Touches no dependency. Always 200 while the process runs. |
| GET    | `/ready`       | Readiness. Probes Postgres and Redis; 503 when either is down. |
| GET    | `/api/v1/meta` | Version, environment, phase, and which providers are mocked. |

`/health` answers "should this container be restarted?" and therefore must not
depend on the database. `/ready` answers "can this instance serve traffic?" and
returns the per-component detail behind the verdict.

## Planned

Phase 1 adds `/api/v1/auth/*` and `/api/v1/users`. Phase 2 adds `/vessels`,
`/voyages` and positions. Phase 4 adds `/optimizations` with the async status
flow. Phase 5 adds `/agent/chat` and `/agent/runs`. Phase 6 adds
`/recommendations`, `/approvals` and `/audit`. Rate limits are applied per
class of endpoint - ordinary reads, agent calls, and optimisation runs get
separate budgets - and idempotency keys guard optimisation creation, approval
and execution.
