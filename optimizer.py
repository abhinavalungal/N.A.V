"""Voyage optimization engine.

Deterministic end to end: routes in, scored options out. Every number the
recommendation quotes comes from this module or the calculators it calls.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from ..clock import utc_now
from ..config import (
    OBJECTIVE_LABELS,
    OBJECTIVE_WEIGHTS,
    OBJECTIVES,
    RISK_ORDER,
)
from ..models import FuelPrice, OptimizationOption, OptimizationRun, Recommendation, Voyage
from . import weather as weather_service
from .emissions import calculate_emissions
from .eta import calculate_eta
from .fuel import calculate_fuel, fuel_cost_usd, weather_factor
from .geo import bearing_deg, relative_angle
from .routing import RouteCandidate, generate_routes


class NoFeasibleOption(Exception):
    """Raised when the constraints rule out every option."""


@dataclass
class Constraints:
    max_speed_kn: float | None = None
    min_speed_kn: float | None = None
    required_arrival_utc: datetime | None = None
    max_weather_risk: str | None = None  # VERY_LOW..SEVERE

    def to_dict(self) -> dict:
        return {
            "max_speed_kn": self.max_speed_kn,
            "min_speed_kn": self.min_speed_kn,
            "required_arrival_utc": self.required_arrival_utc.isoformat()
            if self.required_arrival_utc
            else None,
            "max_weather_risk": self.max_weather_risk,
        }


@dataclass
class EvaluatedOption:
    candidate: RouteCandidate
    fuel_mt: float
    co2_mt: float
    duration_hours: float
    eta_utc: datetime
    risk_index: float
    risk_band: str
    breakdown: dict
    feasible: bool = True
    infeasible_reason: str | None = None
    score: float | None = None
    normalized: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def _track_effects(candidate: RouteCandidate, departure: datetime, duration_hours: float):
    """Weather aggregate, along-track current assist and head-sea exposure."""
    samples = weather_service.sample_along_route(
        candidate.waypoints, departure, duration_hours
    )
    aggregate = weather_service.aggregate(samples)
    if not samples:
        return aggregate, 0.0, 0.7, samples

    assists: list[float] = []
    exposures: list[float] = []
    for i, sample in enumerate(samples):
        a = candidate.waypoints[min(i, len(candidate.waypoints) - 1)]
        b = candidate.waypoints[min(i + 1, len(candidate.waypoints) - 1)]
        course = bearing_deg(a, b) if a != b else 0.0
        angle = relative_angle(course, sample.current_direction_deg)
        assists.append(sample.current_speed_kn * math.cos(math.radians(angle)))
        exposures.append(weather_service.heading_exposure(course, sample))
    return (
        aggregate,
        sum(assists) / len(assists),
        sum(exposures) / len(exposures),
        samples,
    )


def evaluate_route(
    candidate: RouteCandidate,
    *,
    design_speed_kn: float,
    base_consumption_mt_per_day: float,
    fuel_type: str,
    deadweight_t: float,
    departure_utc: datetime,
    bunker_price_usd_per_mt: float | None = None,
) -> EvaluatedOption:
    # First pass with no weather, to get a time base for sampling.
    rough = calculate_eta(candidate.distance_nm, candidate.speed_kn, departure_utc)
    aggregate, current_assist, exposure, _ = _track_effects(
        candidate, departure_utc, rough.duration_hours
    )

    eta = calculate_eta(
        candidate.distance_nm,
        candidate.speed_kn,
        departure_utc,
        current_assist_kn=current_assist,
    )
    wf = weather_factor(
        wave_height_m=aggregate["mean_wave_m"],
        wind_speed_kn=aggregate["mean_wind_kn"],
        head_sea_exposure=exposure,
    )
    fuel = calculate_fuel(
        base_daily_mt=base_consumption_mt_per_day,
        design_speed_kn=design_speed_kn,
        speed_kn=candidate.speed_kn,
        duration_hours=eta.sea_hours,
        weather_multiplier=wf,
    )
    emissions = calculate_emissions(
        fuel.total_mt,
        fuel_type=fuel_type,
        distance_nm=candidate.distance_nm,
        deadweight_t=deadweight_t,
    )

    return EvaluatedOption(
        candidate=candidate,
        fuel_mt=fuel.total_mt,
        co2_mt=emissions.co2_mt,
        duration_hours=eta.duration_hours,
        eta_utc=eta.eta_utc,
        risk_index=aggregate["risk_index"],
        risk_band=aggregate["risk_band"],
        breakdown={
            "fuel": fuel.to_dict(),
            "eta": eta.to_dict(),
            "emissions": emissions.to_dict(),
            "weather": aggregate,
            "current_assist_kn": round(current_assist, 2),
            "head_sea_exposure": round(exposure, 3),
            # Bunker cost at the seeded demo price for this grade. Absent when
            # no price is on file rather than guessed.
            "bunker_price_usd_per_mt": bunker_price_usd_per_mt,
            "cost_usd": (
                fuel_cost_usd(fuel.total_mt, bunker_price_usd_per_mt)
                if bunker_price_usd_per_mt
                else None
            ),
        },
    )


# ---------------------------------------------------------------------------
# Constraints + scoring
# ---------------------------------------------------------------------------


def apply_constraints(options: list[EvaluatedOption], constraints: Constraints) -> None:
    max_risk_rank = (
        RISK_ORDER.index(constraints.max_weather_risk)
        if constraints.max_weather_risk in RISK_ORDER
        else None
    )
    for option in options:
        speed = option.candidate.speed_kn
        reasons = []
        if constraints.max_speed_kn and speed > constraints.max_speed_kn + 1e-6:
            reasons.append(
                f"speed {speed:.1f} kn exceeds the {constraints.max_speed_kn:.1f} kn limit"
            )
        if constraints.min_speed_kn and speed < constraints.min_speed_kn - 1e-6:
            reasons.append(
                f"speed {speed:.1f} kn is below the {constraints.min_speed_kn:.1f} kn minimum"
            )
        if constraints.required_arrival_utc and option.eta_utc > constraints.required_arrival_utc:
            late = (option.eta_utc - constraints.required_arrival_utc).total_seconds() / 3600
            reasons.append(f"arrives {late:.1f} h after the required arrival time")
        if max_risk_rank is not None and RISK_ORDER.index(option.risk_band) > max_risk_rank:
            reasons.append(
                f"weather risk {option.risk_band} exceeds the {constraints.max_weather_risk} limit"
            )
        if reasons:
            option.feasible = False
            option.infeasible_reason = "; ".join(reasons)


def _normalize(values: list[float]) -> list[float]:
    lo, hi = min(values), max(values)
    if math.isclose(lo, hi):
        return [0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def score_options(options: list[EvaluatedOption], objective: str) -> list[EvaluatedOption]:
    feasible = [o for o in options if o.feasible]
    if not feasible:
        return []
    weights = OBJECTIVE_WEIGHTS[objective]
    fuel_n = _normalize([o.fuel_mt for o in feasible])
    eta_n = _normalize([o.duration_hours for o in feasible])
    co2_n = _normalize([o.co2_mt for o in feasible])
    risk_n = _normalize([o.risk_index for o in feasible])
    for i, option in enumerate(feasible):
        option.normalized = {
            "fuel": round(fuel_n[i], 4),
            "eta": round(eta_n[i], 4),
            "co2": round(co2_n[i], 4),
            "risk": round(risk_n[i], 4),
        }
        option.score = round(
            weights["fuel"] * fuel_n[i]
            + weights["eta"] * eta_n[i]
            + weights["co2"] * co2_n[i]
            + weights["risk"] * risk_n[i],
            4,
        )
    return sorted(feasible, key=lambda o: o.score if o.score is not None else 1e9)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def voyage_endpoints(voyage: Voyage):
    """Optimize from where the vessel actually is."""
    if voyage.status == "ACTIVE" and voyage.current_lat is not None:
        origin = (voyage.current_lat, voyage.current_lon)
        origin_label = "current position"
    else:
        origin = voyage.origin_port if voyage.origin_port else (voyage.origin_lat, voyage.origin_lon)
        origin_label = voyage.origin_port
    destination = (
        voyage.destination_port
        if voyage.destination_port
        else (voyage.destination_lat, voyage.destination_lon)
    )
    return origin, destination, origin_label


def build_rationale(
    chosen: EvaluatedOption,
    baseline: EvaluatedOption,
    objective: str,
    weather_source: str,
) -> str:
    fuel_delta = round(baseline.fuel_mt - chosen.fuel_mt, 1)
    co2_delta = round(baseline.co2_mt - chosen.co2_mt, 1)
    hours_delta = round(chosen.duration_hours - baseline.duration_hours, 1)
    pct = round(fuel_delta / baseline.fuel_mt * 100, 1) if baseline.fuel_mt else 0.0

    parts = [
        f"{chosen.candidate.label} scores best for the "
        f"{OBJECTIVE_LABELS[objective].lower()} objective."
    ]
    if chosen.candidate.code == baseline.candidate.code:
        parts.append(
            f"It burns {chosen.fuel_mt:.0f} MT over {chosen.candidate.distance_nm:,.0f} NM "
            f"at {chosen.candidate.speed_kn:.1f} kn and no slower option beats it under the "
            "current constraints."
        )
    else:
        parts.append(
            f"Against the fastest option it saves {fuel_delta:.0f} MT of fuel ({pct:.1f}%) "
            f"and {co2_delta:.0f} MT of CO2, "
            + (
                f"arriving {abs(hours_delta):.1f} h later."
                if hours_delta > 0
                else f"arriving {abs(hours_delta):.1f} h earlier."
            )
        )
    parts.append(
        f"Weather risk along the track is {chosen.risk_band.replace('_', ' ').lower()} "
        f"(mean wind {chosen.breakdown['weather']['mean_wind_kn']:.0f} kn, "
        f"max significant wave height {chosen.breakdown['weather']['max_wave_m']:.1f} m)."
    )
    if weather_source != "OPEN_METEO":
        parts.append("Based on prototype/mock weather data.")
    else:
        parts.append("Based on Open-Meteo forecast data.")
    return " ".join(parts)


def _bunker_price(db: Session, fuel_type: str) -> float | None:
    """Most recent seeded price for this grade, or None if none is on file."""
    row = (
        db.query(FuelPrice)
        .filter(FuelPrice.fuel_type == fuel_type)
        .order_by(FuelPrice.quoted_at.desc())
        .first()
    )
    return row.price_usd_per_mt if row else None


def run_optimization(
    db: Session,
    voyage: Voyage,
    objective: str = "BALANCED",
    constraints: Constraints | None = None,
    persist: bool = True,
) -> OptimizationRun:
    objective = (objective or "BALANCED").upper()
    if objective not in OBJECTIVES:
        raise ValueError(f"Unknown objective '{objective}'. Use one of {', '.join(OBJECTIVES)}")
    constraints = constraints or Constraints()
    vessel = voyage.vessel
    if vessel is None:
        raise ValueError("Voyage has no vessel attached")

    origin, destination, _ = voyage_endpoints(voyage)
    departure = (
        voyage.departure_utc
        if voyage.status == "PLANNED"
        else max(voyage.departure_utc, utc_now().replace(microsecond=0))
    )

    candidates = generate_routes(
        origin,
        destination,
        design_speed_kn=vessel.design_speed_kn,
        departure_utc=departure,
        max_speed_kn=constraints.max_speed_kn,
        min_speed_kn=constraints.min_speed_kn,
    )

    price = _bunker_price(db, vessel.fuel_type)
    evaluated = [
        evaluate_route(
            c,
            design_speed_kn=vessel.design_speed_kn,
            base_consumption_mt_per_day=vessel.base_consumption_mt_per_day,
            fuel_type=vessel.fuel_type,
            deadweight_t=vessel.deadweight_t,
            departure_utc=departure,
            bunker_price_usd_per_mt=price,
        )
        for c in candidates
    ]
    # Two variants can collapse onto the same speed once constraints clamp
    # them; keep the distinct ones.
    seen: set[tuple] = set()
    unique: list[EvaluatedOption] = []
    for option in evaluated:
        key = (round(option.candidate.speed_kn, 2), round(option.candidate.distance_nm, 1))
        if key in seen:
            continue
        seen.add(key)
        unique.append(option)
    evaluated = unique

    apply_constraints(evaluated, constraints)
    ranked = score_options(evaluated, objective)
    weather_source = (
        evaluated[0].breakdown["weather"]["source"] if evaluated else "NONE"
    )

    run = OptimizationRun(
        voyage_id=voyage.id,
        objective=objective,
        constraints_json=constraints.to_dict(),
        weather_source=weather_source,
        status="COMPLETED" if ranked else "NO_FEASIBLE_OPTION",
        message=None
        if ranked
        else "No feasible option found. Every route breaches at least one constraint.",
    )
    db.add(run)
    db.flush()

    stored: dict[str, OptimizationOption] = {}
    for option in evaluated:
        row = OptimizationOption(
            run_id=run.id,
            code=option.candidate.code,
            label=option.candidate.label,
            distance_nm=option.candidate.distance_nm,
            average_speed_kn=option.candidate.speed_kn,
            duration_hours=option.duration_hours,
            eta_utc=option.eta_utc,
            fuel_mt=option.fuel_mt,
            co2_mt=option.co2_mt,
            weather_risk=option.risk_band,
            risk_index=option.risk_index,
            score=option.score,
            feasible=option.feasible,
            infeasible_reason=option.infeasible_reason,
            breakdown_json={**option.breakdown, "normalized": option.normalized},
            geometry_json=option.candidate.geometry,
        )
        db.add(row)
        db.flush()
        stored[option.candidate.code] = row

    if ranked:
        chosen = ranked[0]
        baseline = next(
            (o for o in evaluated if o.candidate.code == "FASTEST" and o.feasible),
            ranked[-1],
        )
        run.recommended_option_id = stored[chosen.candidate.code].id
        run.baseline_option_id = stored[baseline.candidate.code].id
        recommendation = Recommendation(
            run_id=run.id,
            voyage_id=voyage.id,
            option_id=stored[chosen.candidate.code].id,
            headline=f"{chosen.candidate.label} — {chosen.fuel_mt:.0f} MT, "
            f"ETA {chosen.eta_utc.strftime('%d %b %H:%M')} UTC",
            rationale=build_rationale(chosen, baseline, objective, weather_source),
            fuel_saving_mt=round(max(0.0, baseline.fuel_mt - chosen.fuel_mt), 2),
            co2_saving_mt=round(max(0.0, baseline.co2_mt - chosen.co2_mt), 2),
            eta_delta_hours=round(chosen.duration_hours - baseline.duration_hours, 2),
            status="PENDING",
        )
        db.add(recommendation)

    if persist:
        db.commit()
        db.refresh(run)
    else:
        db.flush()
    return run


def activity_steps(run: OptimizationRun) -> list[dict]:
    """High level trace shown in the UI. No hidden reasoning is exposed."""
    voyage = run.voyage
    steps = [
        {"label": f"Retrieved vessel data — {voyage.vessel.name}", "status": "done"},
        {"label": f"Retrieved voyage {voyage.reference}", "status": "done"},
        {
            "label": f"Retrieved weather ({'Open-Meteo' if run.weather_source == 'OPEN_METEO' else 'mock provider'})",
            "status": "done",
        },
        {"label": f"Generated {len(run.options)} route options", "status": "done"},
        {"label": "Calculated fuel and emissions per option", "status": "done"},
        {"label": "Applied constraints", "status": "done"},
    ]
    if run.status == "COMPLETED":
        steps.append({"label": "Scored options and selected a recommendation", "status": "done"})
    else:
        steps.append({"label": "No feasible option found", "status": "failed"})
    return steps
