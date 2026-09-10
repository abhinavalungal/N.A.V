"""Prompts and the text templates used by the mock provider."""

from __future__ import annotations

SYSTEM_PROMPT = """You are N.A.V. (Nautical Agentic Navigator), the assistant inside a
maritime voyage optimization platform.

Rules you must never break:
1. Every number you state must come from a tool result in this conversation.
   Never estimate, interpolate or recall fuel, ETA, distance, emissions,
   weather or vessel figures from memory.
2. If a tool has not given you the figure, say "I don't have enough data to
   calculate this accurately." and name the tool or input that is missing.
3. If a tool result reports a weather source that is not OPEN_METEO, add
   "Based on prototype/mock data." to your answer.
4. Never claim to have changed a voyage, ordered a speed change or controlled a
   vessel. You produce recommendations that a human approves.
5. Be concise and operational: short paragraphs, numbers with units, no filler.
   Fuel and CO2 in metric tonnes (MT), distance in nautical miles (NM), speed in
   knots (kn), times in UTC.

You have tools for vessel data, voyage data, weather, routing, fuel, ETA,
emissions, optimization and voyage history. Call them before answering
anything quantitative."""


def no_data_message(reason: str) -> str:
    return f"I don't have enough data to calculate this accurately. {reason}"


# ---------------------------------------------------------------------------
# Mock provider answer builders. Every value is read from real tool output.
# ---------------------------------------------------------------------------


def _mock_note(source: str | None) -> str:
    return "" if source == "OPEN_METEO" else "\n\nBased on prototype/mock data."


def optimization_answer(result: dict) -> str:
    if result.get("error"):
        return f"Optimization did not complete: {result['error']}"
    if result.get("status") == "NO_FEASIBLE_OPTION":
        return (
            "No feasible option found. "
            f"{result.get('message', '')} "
            "Relax the speed, arrival or weather-risk constraint and run it again."
        )
    rec = result.get("recommendation") or {}
    options = result.get("options", [])
    lines = [
        f"Recommended: {rec.get('label')} for {result.get('objective_label', 'the selected objective').lower()}.",
        "",
        f"Fuel {rec.get('fuel_mt')} MT · CO2 {rec.get('co2_mt')} MT · "
        f"ETA {rec.get('eta_utc')} UTC · risk {str(rec.get('weather_risk', '')).replace('_', ' ').lower()}",
    ]
    if rec.get("fuel_saving_mt"):
        lines.append(
            f"Saving against the fastest option: {rec['fuel_saving_mt']} MT of fuel "
            f"and {rec.get('co2_saving_mt')} MT of CO2, "
            f"{abs(rec.get('eta_delta_hours', 0)):.1f} h "
            f"{'later' if rec.get('eta_delta_hours', 0) > 0 else 'earlier'}."
        )
    if options:
        lines.append("")
        lines.append("Options evaluated:")
        for o in options:
            flag = " (recommended)" if o.get("recommended") else ""
            if not o.get("feasible"):
                lines.append(f"- {o['label']}: excluded — {o.get('infeasible_reason')}")
            else:
                lines.append(
                    f"- {o['label']}: {o['fuel_mt']} MT, ETA {o['eta_utc']}, "
                    f"{o['co2_mt']} MT CO2, risk {str(o['weather_risk']).replace('_', ' ').lower()}{flag}"
                )
    lines.append("")
    lines.append(rec.get("rationale", ""))
    return "\n".join(lines).strip() + _mock_note(result.get("weather_source"))


def explain_answer(result: dict) -> str:
    if result.get("error"):
        return (
            "I don't have an optimization run for this voyage yet. "
            "Run the optimizer and I can explain the choice."
        )
    rec = result.get("recommendation") or {}
    scored = [o for o in result.get("options", []) if o.get("score") is not None]
    lines = [rec.get("rationale", "")]
    if scored:
        lines.append("")
        lines.append("Scores (lower wins, weighted by the selected objective):")
        for o in sorted(scored, key=lambda x: x["score"]):
            lines.append(
                f"- {o['label']}: {o['score']} — fuel {o['fuel_mt']} MT, "
                f"{o['duration_hours']} h, {o['co2_mt']} MT CO2"
            )
    return "\n".join(lines).strip() + _mock_note(result.get("weather_source"))


def weather_answer(result: dict) -> str:
    if result.get("error"):
        return f"I couldn't read the weather: {result['error']}"
    w = result.get("current", {})
    label = "Open-Meteo forecast" if w.get("source") == "OPEN_METEO" else "mock weather field"
    lines = [
        f"Conditions at {w.get('latitude')}, {w.get('longitude')} ({label}):",
        f"Wind {w.get('wind_speed_kn')} kn from {w.get('wind_direction_deg')}°",
        f"Waves {w.get('wave_height_m')} m from {w.get('wave_direction_deg')}°",
        f"Current {w.get('current_speed_kn')} kn setting {w.get('current_direction_deg')}°",
        f"Visibility {w.get('visibility_nm')} NM · air {w.get('temperature_c')} °C",
    ]
    route = result.get("route")
    if route:
        lines.append("")
        lines.append(
            f"Along the remaining track: mean wind {route['mean_wind_kn']} kn, "
            f"max significant wave height {route['max_wave_m']} m, "
            f"risk {str(route['risk_band']).replace('_', ' ').lower()}."
        )
    return "\n".join(lines) + _mock_note(w.get("source"))


def history_answer(result: dict) -> str:
    if result.get("error") or not result.get("voyages"):
        return "I don't have historical voyages for this vessel yet."
    return "\n".join(
        [
            f"Last {result['sample_size']} voyages for {result['vessel_name']}:",
            f"Average speed {result['average_speed_kn']} kn · "
            f"average fuel {result['average_fuel_mt']} MT · "
            f"{result['average_fuel_per_nm_kg']} kg/NM",
            f"Actual fuel ran {result['average_fuel_variance_pct']:+.1f}% against plan; "
            f"arrival ran {result['average_eta_variance_hours']:+.1f} h against plan.",
        ]
    )


def fuel_answer(result: dict) -> str:
    if result.get("error"):
        return f"I couldn't run that calculation: {result['error']}"
    return (
        f"At {result['speed_kn']} kn over {result['distance_nm']:,.0f} NM: "
        f"{result['fuel_mt']} MT of {result['fuel_type']} in {result['duration_hours']} h, "
        f"{result['co2_mt']} MT CO2.\n"
        f"Daily consumption {result['daily_consumption_mt']} MT/day "
        f"(speed factor {result['speed_factor']}, weather factor {result['weather_factor']})."
    )


def voyage_answer(result: dict) -> str:
    if result.get("error"):
        return f"I couldn't find that voyage: {result['error']}"
    v = result
    return (
        f"{v['reference']} — {v['vessel_name']}, {v['origin_port']} to {v['destination_port']}.\n"
        f"Status {v['status']} · {v['distance_remaining_nm']:,.0f} NM remaining of "
        f"{v['distance_nm']:,.0f} NM · speed {v['current_speed_kn']} kn · "
        f"expected arrival {v['expected_arrival_utc']} UTC."
    )


FALLBACK_ANSWER = (
    "I can optimize a voyage, explain a recommendation, read the weather along a "
    "track, run fuel and ETA numbers at a given speed, or compare a voyage with "
    "the vessel's history. Ask me something like \"optimize this voyage for "
    "minimum fuel\" or \"what happens at 14 knots?\"."
)
