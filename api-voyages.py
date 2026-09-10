from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..clock import utc_now
from ..database import get_db
from ..models import HistoricalVoyage, OptimizationRun, Recommendation, Vessel, Voyage
from ..schemas import (
    HazardOut,
    HistoricalVoyageOut,
    HistoryComparison,
    LegOut,
    RouteOptionOut,
    RouteOut,
    VoyageCreate,
    VoyageDetail,
    VoyageOut,
    VoyagePlanOut,
    WeatherOut,
)
from ..services import voyage_plan, weather as weather_service
from ..services.emissions import calculate_emissions
from ..services.eta import calculate_eta
from ..services.fuel import calculate_fuel
from ..services.optimizer import voyage_endpoints
from ..services.ports import PORTS
from ..services.routing import generate_routes, sea_route
from .serializers import recommendation_out, run_out, voyage_out

router = APIRouter(tags=["voyages"])


@router.get("/ports")
def list_ports():
    return [
        {"name": name, "unlocode": p["unlocode"], "country": p["country"], "coord": list(p["coord"])}
        for name, p in sorted(PORTS.items())
    ]


@router.get("/voyages", response_model=list[VoyageOut])
def list_voyages(
    db: Session = Depends(get_db),
    status: str | None = Query(default=None),
    vessel_id: int | None = None,
    limit: int = 200,
):
    query = db.query(Voyage)
    if status:
        query = query.filter(Voyage.status == status.upper())
    if vessel_id:
        query = query.filter(Voyage.vessel_id == vessel_id)
    rows = query.order_by(desc(Voyage.departure_utc)).limit(limit).all()
    return [voyage_out(v) for v in rows]


@router.get("/voyages/{voyage_id}", response_model=VoyageDetail)
def get_voyage(voyage_id: int, db: Session = Depends(get_db)):
    voyage = db.get(Voyage, voyage_id)
    if not voyage:
        raise HTTPException(status_code=404, detail=f"Voyage {voyage_id} not found")

    detail = VoyageDetail.model_validate(voyage)
    detail.vessel_name = voyage.vessel.name
    detail.vessel_imo = voyage.vessel.imo
    detail.progress_pct = (
        round(
            max(0.0, min(100.0, (voyage.distance_nm - voyage.distance_remaining_nm) / voyage.distance_nm * 100)),
            1,
        )
        if voyage.distance_nm
        else 0.0
    )

    points, via, distance = sea_route(
        voyage.origin_port or (voyage.origin_lat, voyage.origin_lon),
        voyage.destination_port or (voyage.destination_lat, voyage.destination_lon),
    )
    from ..services.geo import densify

    detail.route = RouteOut(
        origin=[voyage.origin_lon, voyage.origin_lat],
        destination=[voyage.destination_lon, voyage.destination_lat],
        current=[voyage.current_lon, voyage.current_lat] if voyage.current_lat is not None else None,
        distance_nm=round(distance, 1),
        via=via,
        geometry=[[round(lon, 4), round(lat, 4)] for lat, lon in densify(points, 300.0)],
    )

    lat = voyage.current_lat if voyage.current_lat is not None else voyage.origin_lat
    lon = voyage.current_lon if voyage.current_lon is not None else voyage.origin_lon
    sample = weather_service.get_provider().get(
        (lat, lon), utc_now().replace(microsecond=0)
    )
    detail.weather_now = WeatherOut(
        **sample.to_dict() | {"is_live": sample.source == "OPEN_METEO"}
    )

    run = (
        db.query(OptimizationRun)
        .filter(OptimizationRun.voyage_id == voyage_id)
        .order_by(desc(OptimizationRun.id))
        .first()
    )
    if run:
        detail.latest_run = run_out(db, run)
    pending = (
        db.query(Recommendation)
        .filter(Recommendation.voyage_id == voyage_id, Recommendation.status == "PENDING")
        .order_by(desc(Recommendation.id))
        .first()
    )
    detail.pending_recommendation = recommendation_out(db, pending)
    return detail


@router.post("/voyages", response_model=VoyageOut, status_code=201)
def create_voyage(payload: VoyageCreate, db: Session = Depends(get_db)):
    vessel = db.get(Vessel, payload.vessel_id)
    if not vessel:
        raise HTTPException(status_code=400, detail=f"Vessel {payload.vessel_id} does not exist")

    origin = _endpoint(payload.origin_port, payload.origin_lat, payload.origin_lon, "origin")
    destination = _endpoint(
        payload.destination_port, payload.destination_lat, payload.destination_lon, "destination"
    )

    _points, _via, distance = sea_route(
        payload.origin_port if payload.origin_port in PORTS else origin,
        payload.destination_port if payload.destination_port in PORTS else destination,
    )
    speed = payload.planned_speed_kn or round(vessel.design_speed_kn * 0.92, 1)
    eta = calculate_eta(distance, speed, payload.departure_utc)
    fuel = calculate_fuel(
        base_daily_mt=vessel.base_consumption_mt_per_day,
        design_speed_kn=vessel.design_speed_kn,
        speed_kn=speed,
        duration_hours=eta.sea_hours,
    )

    reference = payload.reference or _next_reference(db, vessel)
    if db.query(Voyage).filter(Voyage.reference == reference).first():
        raise HTTPException(status_code=409, detail=f"Voyage reference {reference} already exists")

    voyage = Voyage(
        reference=reference,
        vessel_id=vessel.id,
        origin_port=payload.origin_port,
        origin_lat=origin[0],
        origin_lon=origin[1],
        destination_port=payload.destination_port,
        destination_lat=destination[0],
        destination_lon=destination[1],
        departure_utc=payload.departure_utc,
        expected_arrival_utc=eta.eta_utc,
        required_arrival_utc=payload.required_arrival_utc,
        current_lat=origin[0],
        current_lon=origin[1],
        current_speed_kn=0.0,
        planned_speed_kn=speed,
        distance_nm=round(distance, 1),
        distance_remaining_nm=round(distance, 1),
        planned_fuel_mt=fuel.total_mt,
        consumed_fuel_mt=0.0,
        cargo_t=payload.cargo_t,
        status="PLANNED",
    )
    db.add(voyage)
    db.commit()
    db.refresh(voyage)
    return voyage_out(voyage)


@router.get("/voyages/{voyage_id}/routes", response_model=list[RouteOptionOut])
def voyage_routes(voyage_id: int, db: Session = Depends(get_db)):
    voyage = db.get(Voyage, voyage_id)
    if not voyage:
        raise HTTPException(status_code=404, detail=f"Voyage {voyage_id} not found")
    origin, destination, _ = voyage_endpoints(voyage)
    routes = generate_routes(
        origin,
        destination,
        voyage.vessel.design_speed_kn,
        max(voyage.departure_utc, utc_now().replace(microsecond=0)),
    )
    return [
        RouteOptionOut(
            code=r.code,
            label=r.label,
            distance_nm=r.distance_nm,
            speed_kn=r.speed_kn,
            via=r.via,
            geometry=r.geometry,
        )
        for r in routes
    ]


@router.get("/voyages/{voyage_id}/plan", response_model=VoyagePlanOut)
def voyage_plan_detail(
    voyage_id: int,
    speed_kn: float | None = None,
    legs: int = 10,
    db: Session = Depends(get_db),
):
    """The passage broken into legs, with the weather expected on each.

    `speed_kn` overrides the planned speed, which is how the voyage page shows
    what a different speed would mean leg by leg. Every figure is recomputed
    from the current forecast, so the total can differ from the fuel figure
    fixed in the plan at departure.
    """
    voyage = db.get(Voyage, voyage_id)
    if not voyage:
        raise HTTPException(status_code=404, detail=f"Voyage {voyage_id} not found")
    if legs < 2 or legs > 24:
        raise HTTPException(status_code=400, detail="legs must be between 2 and 24")

    speed = speed_kn or voyage.planned_speed_kn or voyage.vessel.design_speed_kn
    if speed <= 0:
        raise HTTPException(status_code=400, detail="speed_kn must be positive")

    departure = (
        voyage.departure_utc
        if voyage.status == "PLANNED"
        else max(voyage.departure_utc, utc_now().replace(microsecond=0))
    )
    origin, destination, _ = voyage_endpoints(voyage)
    route = generate_routes(origin, destination, voyage.vessel.design_speed_kn, departure)[0]

    schedule = voyage_plan.leg_schedule(
        route.waypoints, speed, departure, voyage.vessel, max_legs=legs
    )
    hazards = voyage_plan.hazard_segments(schedule)
    live = sum(1 for leg in schedule if leg.weather_source == "OPEN_METEO")
    sources = {leg.weather_source for leg in schedule}

    return VoyagePlanOut(
        voyage_id=voyage.id,
        reference=voyage.reference,
        vessel_name=voyage.vessel.name,
        departure_utc=departure,
        arrival_utc=schedule[-1].arrive_utc if schedule else departure,
        speed_kn=round(speed, 1),
        distance_nm=round(sum(leg.distance_nm for leg in schedule), 1),
        total_fuel_mt=round(sum(leg.fuel_mt for leg in schedule), 2),
        legs=[LegOut(**leg.to_dict()) for leg in schedule],
        hazards=[HazardOut(**hazard.to_dict()) for hazard in hazards],
        weather_source="MIXED" if len(sources) > 1 else (sources.pop() if sources else "NONE"),
        live_fraction=round(live / len(schedule), 3) if schedule else 0.0,
    )


@router.get("/voyages/{voyage_id}/history", response_model=HistoryComparison)
def voyage_history(voyage_id: int, limit: int = 5, db: Session = Depends(get_db)):
    voyage = db.get(Voyage, voyage_id)
    if not voyage:
        raise HTTPException(status_code=404, detail=f"Voyage {voyage_id} not found")
    return _history_for_vessel(db, voyage.vessel, limit, voyage)


@router.get("/vessels/{vessel_id}/history", response_model=HistoryComparison)
def vessel_history(vessel_id: int, limit: int = 10, db: Session = Depends(get_db)):
    vessel = db.get(Vessel, vessel_id)
    if not vessel:
        raise HTTPException(status_code=404, detail=f"Vessel {vessel_id} not found")
    return _history_for_vessel(db, vessel, limit, None)


# --- helpers ---------------------------------------------------------------


def _endpoint(port: str, lat: float | None, lon: float | None, which: str) -> tuple[float, float]:
    if port in PORTS:
        return PORTS[port]["coord"]
    if lat is None or lon is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown {which} port '{port}'. Pass {which}_lat and {which}_lon, "
                "or use a port from GET /api/v1/ports."
            ),
        )
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise HTTPException(status_code=400, detail=f"Invalid {which} coordinates")
    return (lat, lon)


def _next_reference(db: Session, vessel: Vessel) -> str:
    count = db.query(Voyage).filter(Voyage.vessel_id == vessel.id).count() + 1
    initials = "".join(word[0] for word in vessel.name.split()[:2]).upper()
    return f"{initials}-{utc_now():%Y}-{count:03d}"


def _history_for_vessel(
    db: Session, vessel: Vessel, limit: int, voyage: Voyage | None
) -> HistoryComparison:
    rows = (
        db.query(HistoricalVoyage)
        .filter(HistoricalVoyage.vessel_id == vessel.id)
        .order_by(desc(HistoricalVoyage.departure_utc))
        .limit(limit)
        .all()
    )
    n = len(rows) or 1
    fuel_variance = (
        sum((r.actual_fuel_mt - r.predicted_fuel_mt) / r.predicted_fuel_mt * 100 for r in rows) / n
        if rows
        else 0.0
    )
    return HistoryComparison(
        vessel_id=vessel.id,
        vessel_name=vessel.name,
        sample_size=len(rows),
        average_speed_kn=round(sum(r.average_speed_kn for r in rows) / n, 2) if rows else 0.0,
        average_fuel_mt=round(sum(r.actual_fuel_mt for r in rows) / n, 1) if rows else 0.0,
        average_fuel_per_nm_kg=round(
            sum(r.actual_fuel_mt * 1000 / r.distance_nm for r in rows) / n, 2
        )
        if rows
        else 0.0,
        average_duration_hours=round(sum(r.actual_duration_hours for r in rows) / n, 1)
        if rows
        else 0.0,
        average_fuel_variance_pct=round(fuel_variance, 2),
        average_eta_variance_hours=round(
            sum(r.actual_duration_hours - r.predicted_duration_hours for r in rows) / n, 2
        )
        if rows
        else 0.0,
        voyages=[HistoricalVoyageOut.model_validate(r) for r in rows],
        current_voyage=voyage_out(voyage) if voyage else None,
    )


@router.get("/voyages/{voyage_id}/emissions")
def voyage_emissions(voyage_id: int, db: Session = Depends(get_db)):
    voyage = db.get(Voyage, voyage_id)
    if not voyage:
        raise HTTPException(status_code=404, detail=f"Voyage {voyage_id} not found")
    result = calculate_emissions(
        voyage.planned_fuel_mt,
        voyage.vessel.fuel_type,
        voyage.distance_nm,
        voyage.vessel.deadweight_t,
    )
    return {"voyage_id": voyage.id, "planned_fuel_mt": voyage.planned_fuel_mt, **result.to_dict()}
