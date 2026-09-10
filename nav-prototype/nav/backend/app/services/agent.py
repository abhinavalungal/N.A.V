"""The N.A.V. agent.

Tools do the maths against the database and the deterministic services; the
LLM only decides which tool to call and how to phrase the result.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..clock import utc_now
from ..ai.prompts import SYSTEM_PROMPT
from ..ai.provider import AIProvider, ToolCall, get_ai_provider
from ..config import OBJECTIVE_LABELS
from ..models import (
    AgentRun,
    ChatMessage,
    HistoricalVoyage,
    OptimizationRun,
    Vessel,
    Voyage,
)
from . import weather as weather_service
from .emissions import calculate_emissions
from .eta import calculate_eta
from .fuel import calculate_fuel, weather_factor
from .optimizer import Constraints, run_optimization
from .routing import generate_routes, route_summary

MAX_ITERATIONS = 4


# ---------------------------------------------------------------------------
# Tool schemas (OpenAI function-calling format)
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict] = [
    {
        "name": "get_vessel",
        "description": "Vessel particulars: IMO, type, deadweight, speeds, fuel, position.",
        "parameters": {
            "type": "object",
            "properties": {
                "vessel_id": {"type": "integer"},
                "name": {"type": "string"},
                "voyage_id": {"type": "integer"},
            },
        },
    },
    {
        "name": "get_voyage",
        "description": "Voyage details: ports, dates, distance, progress, status.",
        "parameters": {
            "type": "object",
            "properties": {
                "voyage_id": {"type": "integer"},
                "reference": {"type": "string"},
            },
        },
    },
    {
        "name": "get_weather",
        "description": "Weather at the vessel position and aggregated along the remaining track.",
        "parameters": {
            "type": "object",
            "properties": {
                "voyage_id": {"type": "integer"},
                "vessel_id": {"type": "integer"},
            },
        },
    },
    {
        "name": "get_routes",
        "description": "Candidate routes between the voyage origin (or current position) and destination.",
        "parameters": {
            "type": "object",
            "properties": {"voyage_id": {"type": "integer"}},
        },
    },
    {
        "name": "calculate_fuel",
        "description": "Deterministic fuel and CO2 for a distance and speed. Use for what-if speed questions.",
        "parameters": {
            "type": "object",
            "properties": {
                "voyage_id": {"type": "integer"},
                "vessel_id": {"type": "integer"},
                "speed_kn": {"type": "number"},
                "distance_nm": {"type": "number"},
            },
        },
    },
    {
        "name": "calculate_eta",
        "description": "Deterministic ETA from distance and speed.",
        "parameters": {
            "type": "object",
            "properties": {
                "voyage_id": {"type": "integer"},
                "speed_kn": {"type": "number"},
                "distance_nm": {"type": "number"},
            },
        },
    },
    {
        "name": "calculate_emissions",
        "description": "CO2 from a fuel quantity using IMO/EU MRV emission factors.",
        "parameters": {
            "type": "object",
            "properties": {
                "fuel_mt": {"type": "number"},
                "fuel_type": {"type": "string"},
                "distance_nm": {"type": "number"},
            },
            "required": ["fuel_mt"],
        },
    },
    {
        "name": "optimize_voyage",
        "description": "Run the optimizer and produce a recommendation for a voyage.",
        "parameters": {
            "type": "object",
            "properties": {
                "voyage_id": {"type": "integer"},
                "objective": {
                    "type": "string",
                    "enum": ["MIN_FUEL", "FASTEST", "MIN_EMISSIONS", "BALANCED"],
                },
                "max_speed_kn": {"type": "number"},
                "min_speed_kn": {"type": "number"},
                "max_weather_risk": {
                    "type": "string",
                    "enum": ["VERY_LOW", "LOW", "MODERATE", "HIGH", "SEVERE"],
                },
            },
        },
    },
    {
        "name": "get_historical_voyages",
        "description": "Completed voyages for a vessel with actual versus predicted fuel and duration.",
        "parameters": {
            "type": "object",
            "properties": {
                "vessel_id": {"type": "integer"},
                "voyage_id": {"type": "integer"},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "get_latest_optimization",
        "description": "The most recent optimization run for a voyage, with option scores and the recommendation.",
        "parameters": {
            "type": "object",
            "properties": {"voyage_id": {"type": "integer"}},
        },
    },
]

TOOL_LABELS = {
    "get_vessel": "Retrieved vessel data",
    "get_voyage": "Retrieved voyage data",
    "get_weather": "Retrieved weather",
    "get_routes": "Generated route options",
    "calculate_fuel": "Calculated fuel",
    "calculate_eta": "Calculated ETA",
    "calculate_emissions": "Calculated emissions",
    "optimize_voyage": "Evaluated options and scored them",
    "get_historical_voyages": "Retrieved voyage history",
    "get_latest_optimization": "Read the last optimization run",
}


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def _voyage(db: Session, args: dict, fallback_voyage_id: int | None) -> Voyage | None:
    voyage_id = args.get("voyage_id") or fallback_voyage_id
    if voyage_id:
        voyage = db.get(Voyage, int(voyage_id))
        if voyage:
            return voyage
    if args.get("reference"):
        return db.query(Voyage).filter(Voyage.reference == args["reference"]).first()
    return db.query(Voyage).filter(Voyage.status == "ACTIVE").order_by(Voyage.id).first()


def _vessel(db: Session, args: dict, fallback_voyage_id: int | None) -> Vessel | None:
    if args.get("vessel_id"):
        vessel = db.get(Vessel, int(args["vessel_id"]))
        if vessel:
            return vessel
    if args.get("name"):
        return db.query(Vessel).filter(Vessel.name.ilike(f"%{args['name']}%")).first()
    voyage = _voyage(db, args, fallback_voyage_id)
    return voyage.vessel if voyage else None


def _voyage_payload(voyage: Voyage) -> dict:
    return {
        "voyage_id": voyage.id,
        "reference": voyage.reference,
        "vessel_id": voyage.vessel_id,
        "vessel_name": voyage.vessel.name,
        "origin_port": voyage.origin_port,
        "destination_port": voyage.destination_port,
        "departure_utc": voyage.departure_utc.strftime("%d %b %Y %H:%M"),
        "expected_arrival_utc": voyage.expected_arrival_utc.strftime("%d %b %Y %H:%M"),
        "distance_nm": voyage.distance_nm,
        "distance_remaining_nm": voyage.distance_remaining_nm,
        "current_speed_kn": voyage.current_speed_kn,
        "planned_speed_kn": voyage.planned_speed_kn,
        "planned_fuel_mt": voyage.planned_fuel_mt,
        "consumed_fuel_mt": voyage.consumed_fuel_mt,
        "status": voyage.status,
    }


def _run_payload(db: Session, run: OptimizationRun) -> dict:
    options = []
    for o in run.options:
        options.append(
            {
                "id": o.id,
                "code": o.code,
                "label": o.label,
                "distance_nm": o.distance_nm,
                "speed_kn": o.average_speed_kn,
                "duration_hours": o.duration_hours,
                "eta_utc": o.eta_utc.strftime("%d %b %H:%M"),
                "fuel_mt": o.fuel_mt,
                "co2_mt": o.co2_mt,
                "weather_risk": o.weather_risk,
                "score": o.score,
                "feasible": o.feasible,
                "infeasible_reason": o.infeasible_reason,
                "recommended": o.id == run.recommended_option_id,
            }
        )
    rec = run.recommendation
    payload = {
        "run_id": run.id,
        "voyage_id": run.voyage_id,
        "status": run.status,
        "message": run.message,
        "objective": run.objective,
        "objective_label": OBJECTIVE_LABELS.get(run.objective, run.objective),
        "weather_source": run.weather_source,
        "options": options,
    }
    if rec:
        chosen = next((o for o in options if o["id"] == rec.option_id), {})
        payload["recommendation"] = {
            "recommendation_id": rec.id,
            "label": chosen.get("label"),
            "fuel_mt": chosen.get("fuel_mt"),
            "co2_mt": chosen.get("co2_mt"),
            "eta_utc": chosen.get("eta_utc"),
            "weather_risk": chosen.get("weather_risk"),
            "fuel_saving_mt": rec.fuel_saving_mt,
            "co2_saving_mt": rec.co2_saving_mt,
            "eta_delta_hours": rec.eta_delta_hours,
            "rationale": rec.rationale,
            "status": rec.status,
        }
    return payload


def tool_get_vessel(db: Session, args: dict, ctx: int | None) -> dict:
    vessel = _vessel(db, args, ctx)
    if not vessel:
        return {"error": "vessel not found"}
    return {
        "vessel_id": vessel.id,
        "imo": vessel.imo,
        "name": vessel.name,
        "vessel_type": vessel.vessel_type,
        "deadweight_t": vessel.deadweight_t,
        "design_speed_kn": vessel.design_speed_kn,
        "current_speed_kn": vessel.current_speed_kn,
        "fuel_type": vessel.fuel_type,
        "base_consumption_mt_per_day": vessel.base_consumption_mt_per_day,
        "latitude": vessel.latitude,
        "longitude": vessel.longitude,
        "status": vessel.status,
        "data_source": vessel.data_source,
    }


def tool_get_voyage(db: Session, args: dict, ctx: int | None) -> dict:
    voyage = _voyage(db, args, ctx)
    if not voyage:
        return {"error": "voyage not found"}
    return _voyage_payload(voyage)


def tool_get_weather(db: Session, args: dict, ctx: int | None) -> dict:
    voyage = _voyage(db, args, ctx)
    vessel = _vessel(db, args, ctx)
    if not vessel and not voyage:
        return {"error": "no vessel or voyage in context"}
    lat = voyage.current_lat if voyage and voyage.current_lat is not None else vessel.latitude
    lon = voyage.current_lon if voyage and voyage.current_lon is not None else vessel.longitude
    now = utc_now().replace(microsecond=0)
    current = weather_service.get_provider().get((lat, lon), now)
    payload: dict = {"current": current.to_dict()}
    if voyage:
        from .optimizer import voyage_endpoints

        origin, destination, _ = voyage_endpoints(voyage)
        routes = generate_routes(
            origin, destination, vessel.design_speed_kn, now
        )
        samples = weather_service.sample_along_route(
            routes[0].waypoints,
            now,
            routes[0].distance_nm / max(1.0, routes[0].speed_kn),
            max_samples=8,
        )
        payload["route"] = weather_service.aggregate(samples)
        payload["voyage_id"] = voyage.id
    return payload


def tool_get_routes(db: Session, args: dict, ctx: int | None) -> dict:
    voyage = _voyage(db, args, ctx)
    if not voyage:
        return {"error": "voyage not found"}
    from .optimizer import voyage_endpoints

    origin, destination, _ = voyage_endpoints(voyage)
    routes = generate_routes(
        origin,
        destination,
        voyage.vessel.design_speed_kn,
        max(voyage.departure_utc, utc_now().replace(microsecond=0)),
    )
    return {"voyage_id": voyage.id, "routes": [route_summary(r) for r in routes]}


def tool_calculate_fuel(db: Session, args: dict, ctx: int | None) -> dict:
    vessel = _vessel(db, args, ctx)
    if not vessel:
        return {"error": "vessel not found"}
    voyage = _voyage(db, args, ctx)
    distance = float(
        args.get("distance_nm")
        or (voyage.distance_remaining_nm if voyage else 0)
        or (voyage.distance_nm if voyage else 0)
    )
    if distance <= 0:
        return {"error": "no distance available for this calculation"}
    speed = float(args.get("speed_kn") or vessel.current_speed_kn or vessel.design_speed_kn)
    if speed <= 0:
        return {"error": "speed must be greater than zero"}

    now = utc_now().replace(microsecond=0)
    sample = weather_service.get_provider().get((vessel.latitude, vessel.longitude), now)
    wf = weather_factor(sample.wave_height_m, sample.wind_speed_kn)
    eta = calculate_eta(distance, speed, now)
    fuel = calculate_fuel(
        base_daily_mt=vessel.base_consumption_mt_per_day,
        design_speed_kn=vessel.design_speed_kn,
        speed_kn=speed,
        duration_hours=eta.sea_hours,
        weather_multiplier=wf,
    )
    emissions = calculate_emissions(
        fuel.total_mt, vessel.fuel_type, distance, vessel.deadweight_t
    )
    return {
        "vessel_id": vessel.id,
        "voyage_id": voyage.id if voyage else None,
        "distance_nm": distance,
        "speed_kn": speed,
        "duration_hours": eta.duration_hours,
        "fuel_mt": fuel.total_mt,
        "co2_mt": emissions.co2_mt,
        "daily_consumption_mt": fuel.daily_mt,
        "speed_factor": fuel.speed_factor,
        "weather_factor": fuel.weather_factor,
        "fuel_type": vessel.fuel_type,
        "emission_factor": emissions.emission_factor,
        "eta_utc": eta.eta_utc.strftime("%d %b %Y %H:%M"),
        "weather_source": sample.source,
    }


def tool_calculate_eta(db: Session, args: dict, ctx: int | None) -> dict:
    voyage = _voyage(db, args, ctx)
    if not voyage:
        return {"error": "voyage not found"}
    distance = float(args.get("distance_nm") or voyage.distance_remaining_nm or voyage.distance_nm)
    speed = float(
        args.get("speed_kn") or voyage.current_speed_kn or voyage.planned_speed_kn
    )
    if speed <= 0:
        return {"error": "vessel speed is zero, cannot calculate an ETA"}
    now = utc_now().replace(microsecond=0)
    start = now if voyage.status == "ACTIVE" else voyage.departure_utc
    eta = calculate_eta(distance, speed, start)
    delta = (eta.eta_utc - voyage.expected_arrival_utc).total_seconds() / 3600.0
    return {
        "voyage_id": voyage.id,
        "distance_nm": distance,
        "speed_kn": speed,
        "duration_hours": eta.duration_hours,
        "sea_hours": eta.sea_hours,
        "port_allowance_hours": eta.port_allowance_hours,
        "eta_utc": eta.eta_utc.strftime("%d %b %Y %H:%M"),
        "scheduled_arrival_utc": voyage.expected_arrival_utc.strftime("%d %b %Y %H:%M"),
        "variance_hours": round(delta, 2),
    }


def tool_calculate_emissions(db: Session, args: dict, ctx: int | None) -> dict:
    try:
        result = calculate_emissions(
            float(args.get("fuel_mt", 0)),
            args.get("fuel_type", "VLSFO"),
            args.get("distance_nm"),
        )
    except ValueError as exc:
        return {"error": str(exc)}
    return {"fuel_mt": float(args.get("fuel_mt", 0)), **result.to_dict()}


def tool_optimize_voyage(db: Session, args: dict, ctx: int | None) -> dict:
    voyage = _voyage(db, args, ctx)
    if not voyage:
        return {"error": "voyage not found"}
    constraints = Constraints(
        max_speed_kn=args.get("max_speed_kn"),
        min_speed_kn=args.get("min_speed_kn"),
        required_arrival_utc=voyage.required_arrival_utc,
        max_weather_risk=args.get("max_weather_risk"),
    )
    try:
        run = run_optimization(db, voyage, args.get("objective", "BALANCED"), constraints)
    except ValueError as exc:
        return {"error": str(exc)}
    return _run_payload(db, run)


def tool_get_historical_voyages(db: Session, args: dict, ctx: int | None) -> dict:
    vessel = _vessel(db, args, ctx)
    if not vessel:
        return {"error": "vessel not found"}
    limit = int(args.get("limit") or 5)
    rows = (
        db.query(HistoricalVoyage)
        .filter(HistoricalVoyage.vessel_id == vessel.id)
        .order_by(desc(HistoricalVoyage.departure_utc))
        .limit(limit)
        .all()
    )
    if not rows:
        return {"error": "no historical voyages", "vessel_name": vessel.name, "voyages": []}
    n = len(rows)
    fuel_var = sum(
        (r.actual_fuel_mt - r.predicted_fuel_mt) / r.predicted_fuel_mt * 100 for r in rows
    ) / n
    eta_var = sum(r.actual_duration_hours - r.predicted_duration_hours for r in rows) / n
    return {
        "vessel_id": vessel.id,
        "vessel_name": vessel.name,
        "sample_size": n,
        "average_speed_kn": round(sum(r.average_speed_kn for r in rows) / n, 2),
        "average_fuel_mt": round(sum(r.actual_fuel_mt for r in rows) / n, 1),
        "average_fuel_per_nm_kg": round(
            sum(r.actual_fuel_mt * 1000 / r.distance_nm for r in rows) / n, 2
        ),
        "average_duration_hours": round(sum(r.actual_duration_hours for r in rows) / n, 1),
        "average_fuel_variance_pct": round(fuel_var, 2),
        "average_eta_variance_hours": round(eta_var, 2),
        "voyages": [
            {
                "reference": r.reference,
                "route": f"{r.origin_port} - {r.destination_port}",
                "distance_nm": r.distance_nm,
                "average_speed_kn": r.average_speed_kn,
                "actual_fuel_mt": r.actual_fuel_mt,
                "predicted_fuel_mt": r.predicted_fuel_mt,
                "co2_mt": r.co2_mt,
            }
            for r in rows
        ],
    }


def tool_get_latest_optimization(db: Session, args: dict, ctx: int | None) -> dict:
    voyage = _voyage(db, args, ctx)
    if not voyage:
        return {"error": "voyage not found"}
    run = (
        db.query(OptimizationRun)
        .filter(OptimizationRun.voyage_id == voyage.id)
        .order_by(desc(OptimizationRun.id))
        .first()
    )
    if not run:
        return {"error": "no optimization run for this voyage yet"}
    return _run_payload(db, run)


TOOLS = {
    "get_vessel": tool_get_vessel,
    "get_voyage": tool_get_voyage,
    "get_weather": tool_get_weather,
    "get_routes": tool_get_routes,
    "calculate_fuel": tool_calculate_fuel,
    "calculate_eta": tool_calculate_eta,
    "calculate_emissions": tool_calculate_emissions,
    "optimize_voyage": tool_optimize_voyage,
    "get_historical_voyages": tool_get_historical_voyages,
    "get_latest_optimization": tool_get_latest_optimization,
}


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------


def _context_block(db: Session, voyage_id: int | None) -> str:
    if not voyage_id:
        return "No voyage is open in the UI. Ask the user which voyage they mean if it matters."
    voyage = db.get(Voyage, voyage_id)
    if not voyage:
        return "No voyage is open in the UI."
    return (
        f"The user is looking at active voyage id: {voyage.id} "
        f"({voyage.reference}, {voyage.vessel.name}, {voyage.origin_port} to "
        f"{voyage.destination_port}, status {voyage.status})."
    )


def _history(db: Session, session_id: str, limit: int = 6) -> list[dict]:
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(desc(ChatMessage.id))
        .limit(limit)
        .all()
    )
    return [{"role": r.role, "content": r.content} for r in reversed(rows)]


def run_agent(
    db: Session,
    message: str,
    session_id: str = "default",
    voyage_id: int | None = None,
    provider: AIProvider | None = None,
) -> dict:
    started = time.perf_counter()
    provider = provider or get_ai_provider()

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": _context_block(db, voyage_id)},
        *_history(db, session_id),
        {"role": "user", "content": message},
    ]

    steps: list[dict] = []
    data: dict = {}
    answer = ""
    status = "COMPLETED"

    for _ in range(MAX_ITERATIONS):
        try:
            response = provider.complete(messages, TOOL_SCHEMAS)
        except Exception as exc:  # noqa: BLE001 - provider failures must not 500
            status = "AI_ERROR"
            answer = (
                "The language model is unavailable, so I can't answer in words right now. "
                f"({type(exc).__name__}) The optimizer and calculations still work from the UI."
            )
            break

        if not response.tool_calls:
            answer = response.text or ""
            break

        messages.append(
            {
                "role": "assistant",
                "content": response.text or None,
                "tool_calls": [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {"name": c.name, "arguments": json.dumps(c.arguments)},
                    }
                    for c in response.tool_calls
                ],
            }
        )
        for call in response.tool_calls:
            result = _execute(db, call, voyage_id)
            steps.append(
                {
                    "tool": call.name,
                    "label": TOOL_LABELS.get(call.name, call.name),
                    "status": "failed" if result.get("error") else "done",
                    "detail": result.get("error"),
                }
            )
            if call.name in ("optimize_voyage", "get_latest_optimization") and not result.get("error"):
                data["run_id"] = result.get("run_id")
                data["voyage_id"] = result.get("voyage_id")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": call.name,
                    "content": json.dumps(result, default=str),
                }
            )

    if not answer:
        answer = (
            "I don't have enough data to answer that accurately. "
            "Try naming the voyage or the vessel."
        )

    duration_ms = int((time.perf_counter() - started) * 1000)
    db.add(ChatMessage(session_id=session_id, voyage_id=voyage_id, role="user", content=message))
    db.add(
        ChatMessage(session_id=session_id, voyage_id=voyage_id, role="assistant", content=answer)
    )
    run = AgentRun(
        session_id=session_id,
        voyage_id=voyage_id,
        question=message,
        answer=answer,
        provider=provider.name,
        steps_json=steps,
        duration_ms=duration_ms,
        status=status,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    return {
        "session_id": session_id,
        "answer": answer,
        "provider": provider.name,
        "steps": steps,
        "data": data,
        "duration_ms": duration_ms,
        "run_id": run.id,
    }


def _execute(db: Session, call: ToolCall, voyage_id: int | None) -> dict:
    fn = TOOLS.get(call.name)
    if fn is None:
        return {"error": f"unknown tool '{call.name}'"}
    try:
        return fn(db, call.arguments or {}, voyage_id)
    except Exception as exc:  # noqa: BLE001 - a tool failure is data, not a crash
        db.rollback()
        return {"error": f"{type(exc).__name__}: {exc}"}


def recent_runs(db: Session, limit: int = 20) -> list[AgentRun]:
    return db.query(AgentRun).order_by(desc(AgentRun.id)).limit(limit).all()


def timedelta_hours(a: datetime, b: datetime) -> float:
    return (a - b) / timedelta(hours=1)
