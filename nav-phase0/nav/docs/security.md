# Security

## Implemented in Phase 0

- No secret in source. Every credential is read from the environment;
  `.env` is git-ignored and `.env.example` carries placeholders only.
- `JWT_SECRET` has no default. The process refuses to start without it rather
  than falling back to a guessable value.
- Security headers on every response: `X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy`, `Cross-Origin-Opener-Policy`,
  `Permissions-Policy`.
- CORS origins come from configuration, not a wildcard.
- Request validation through Pydantic; validation failures return a structured
  422 without echoing internals.
- Unhandled exceptions log a stack trace server-side and return a generic
  message with the request id. Driver errors never reach the client.
- Containers run as non-root (`uid 10001` api and worker, `10002` web).
- Postgres and Redis are reachable only over the compose network in a real
  deployment; the published host ports are a local development convenience.

## Planned

Phase 1: JWT authentication, password hashing, RBAC, tenant isolation enforced
in the repository layer, authorisation middleware, rate limiting per endpoint
class.

Multi-tenancy is a data rule, not a UI rule: every tenant-owned row carries
`company_id` and every query filters on it, so a user of one company cannot
reach another company's data even through a crafted request. Agent memory and
retrieved documents are scoped the same way.

Phase 9: uploaded documents are type-checked, size-limited, scanned where the
infrastructure allows, and never executed.

## Prompt injection

External text - master messages, documents, emails, third-party API responses -
is treated as untrusted data throughout. It cannot alter system policy, tool
permissions, or approval state. Tool authorisation is checked server-side on
every call, so a successful injection still cannot exceed the caller's
permissions.

## Audit

From Phase 6, every login, agent run, tool call, recommendation, approval,
rejection, modification, execution and data change is recorded with company,
user, action, resource, timestamp and metadata. Audit rows are append-only
through normal application paths.
