# Regulatory architecture

Planned for a later phase, but the shape is fixed now because it constrains
earlier design.

## Rules

Regulatory logic lives in deterministic services. It is never expressed in a
prompt, and the LLM's only role is explaining a result it was given.

Constants are never scattered through the code. Every regulation carries a
version, a formula, its factors and an effective date:

    FuelEU-2026-v1
    EU-ETS-2026-v1

A calculated record stores the regulatory version used. When a factor changes,
a new version is added; historical records keep the version they were
calculated under and are not silently recomputed.

## FuelEU Maritime

Interfaces to prepare: energy in scope, GHG intensity, compliance balance,
pooling, banking, borrowing, penalty, fuel type, voyage scope.

## EU ETS

Interfaces to prepare: scope determination for EU, non-EU and partial voyages,
emissions, allowances, cost, and forecast.

## Boundary with the rest of the platform

Emissions calculation (fuel consumed times a versioned emission factor) is a
Phase 3 service and is deliberately separate from regulatory treatment of
those emissions. Compliance surfaces as its own agent later, sitting on the
same deterministic engines rather than reimplementing them.
