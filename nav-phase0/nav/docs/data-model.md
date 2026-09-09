# Data model

The tables below are the plan, grouped by the phase that creates them. Only
the conventions in `database.md` and the baseline migration exist today.

## Phase 1 - identity and tenancy

    companies
    users, roles, permissions, user_roles

## Phase 2 - fleet and voyages

    vessels
      id, imo_number (unique), vessel_name, vessel_type, company_id, flag,
      deadweight, gross_tonnage, length_m, beam_m, draft_m,
      design_speed_knots, main_engine_power_kw, fuel_type,
      design_fuel_consumption_mt_day, status, created_at, updated_at

    vessel_specs

    vessel_positions
      vessel_id, latitude, longitude, speed_knots, course_deg, heading_deg,
      timestamp, source, quality_status

    voyages
      id, voyage_reference, company_id, vessel_id,
      departure_port, destination_port,
      departure_lat, departure_lon, destination_lat, destination_lon,
      planned_departure, planned_arrival, actual_departure, actual_arrival,
      current_lat, current_lon, current_speed_knots, status,
      created_at, updated_at

    voyage_waypoints, voyage_routes

Voyage status: `PLANNED`, `ACTIVE`, `COMPLETED`, `CANCELLED`, `PAUSED`.
Position quality: `FRESH`, `STALE`, `MISSING`, `ESTIMATED`, `MOCK`, `INVALID`.
A missing position is stored as missing. It is never filled in with a guess.

## Phase 3 - environment and fuel

    weather_observations, weather_forecasts
    fuel_types, fuel_prices, fuel_consumption_models, bunkering_events
    emissions_records

## Phase 4 - optimisation

    optimization_runs, optimization_options, optimization_constraints

## Phase 5 and 6 - agent, decisions, audit

    agent_runs, agent_actions, tool_calls
    recommendations, approvals
    messages, master_feedback
    audit_logs

Recommendation states: `DRAFT`, `PENDING_APPROVAL`, `APPROVED`, `REJECTED`,
`MODIFIED`, `EXECUTED`, `EXPIRED`. Invalid transitions are rejected, state
changes run inside a transaction, and a modification never overwrites the
original - it is recorded alongside it with the user, timestamp and reason.

## Phase 8 and 9 - learning and knowledge

    voyage_outcomes            predicted versus actual fuel, ETA, distance,
                               emissions, and the resulting error
    model_versions             model name, version, training data version
    regulatory_versions        regulation, formula, factor, effective date
    documents, document_chunks pgvector embeddings, each chunk keeping
                               document_id, source, section, version
