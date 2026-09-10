# Optimisation

Planned for Phase 4, with the deterministic services it depends on landing in
Phase 3. The `optimization/` package at the repository root is where the maths
lives, deliberately outside the web application.

## Inputs and objectives

Inputs: vessel, voyage, weather, fuel model, fuel price, constraints,
objective. Objectives: `MIN_FUEL`, `MIN_COST`, `FASTEST_ETA`,
`MIN_EMISSIONS`, `BALANCED`, `CUSTOM` with explicit weights, for example
fuel 0.40, ETA 0.30, emissions 0.20, weather risk 0.10.

## Hard versus soft

Hard constraints are never traded off: maximum and minimum speed, draft, port
and area restrictions, arrival deadlines, operational limits. When no solution
satisfies them the answer is `NO_FEASIBLE_SOLUTION` plus the constraints that
conflict. A fabricated solution is worse than no solution.

Soft objectives are traded off against each other under the configured
weights: fuel, ETA preference, emissions, comfort, cost.

The optimiser reports at least three feasible options where they exist, ranks
them, and states why the recommended one wins.

## Determinism and reproducibility

Every run stores its input snapshot, constraints, objective, weather and fuel
data, and the version of each model used. Re-running a stored snapshot must
produce the same result; a past decision is never reconstructed from live data
that has since moved.

    Recommendation NAV-REC-123
      data snapshot   DATA-2026-09-09-001
      optimisation    OPT-v1.0.0
      fuel model      FUEL-v1.0.0
      agent           NAV-AGENT-v1.0.0

## Models

Fuel consumption starts as a configurable, versioned analytical model
(base consumption, non-linear speed factor, weather factor) with no
vessel-specific constants baked into code. Historical regression and learned
models follow, tracked by `model_versions` with MAE, RMSE and MAPE measured
against `voyage_outcomes`. Model accuracy is tracked separately from anything
the LLM does.
