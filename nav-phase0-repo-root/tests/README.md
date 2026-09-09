# Tests

Backend unit and integration tests live next to the code they cover, in
`apps/api/tests`, and run with `cd apps/api && python -m pytest`.

`e2e/` holds the Playwright suite, added in Phase 7 when there are screens to
drive. The first journey it will cover: log in, create a vessel, create a
voyage, run an optimisation, review the recommendation, approve it, see the
result.

The Phase 0 suite deliberately runs with no Postgres, no Redis and no network:
dependency probes are pointed at closed ports so the failure path is exercised
rather than mocked away.
