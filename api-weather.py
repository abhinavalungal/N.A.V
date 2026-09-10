from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..clock import utc_now
from ..database import get_db
from ..models import Vessel, Voyage, WeatherRecord
from ..schemas import RouteWeatherOut, WeatherOut
from ..services import weather as weather_service
from ..services.optimizer import voyage_endpoints
from ..services.routing import generate_routes

router = APIRouter(tags=["weather"])


def _out(sample) -> WeatherOut:
    return WeatherOut(**sample.to_dict() | {"is_live": sample.source == "OPEN_METEO"})


def _store(db: Session, sample) -> None:
    db.add(
        WeatherRecord(
            latitude=sample.latitude,
            longitude=sample.longitude,
            valid_at=sample.valid_at,
            wind_speed_kn=sample.wind_speed_kn,
            wind_direction_deg=sample.wind_direction_deg,
            wave_height_m=sample.wave_height_m,
            wave_direction_deg=sample.wave_direction_deg,
            current_speed_kn=sample.current_speed_kn,
            current_direction_deg=sample.current_direction_deg,
            visibility_nm=sample.visibility_nm,
            temperature_c=sample.temperature_c,
            wave_period_s=sample.wave_period_s,
            swell_wave_height_m=sample.swell_wave_height_m,
            source=sample.source,
        )
    )
    db.commit()


@router.get("/weather/{vessel_id}", response_model=WeatherOut)
def vessel_weather(vessel_id: int, db: Session = Depends(get_db)):
    vessel = db.get(Vessel, vessel_id)
    if not vessel:
        raise HTTPException(status_code=404, detail=f"Vessel {vessel_id} not found")
    sample = weather_service.get_provider().get(
        (vessel.latitude, vessel.longitude), utc_now().replace(microsecond=0)
    )
    _store(db, sample)
    return _out(sample)


@router.get("/weather/point/{lat}/{lon}", response_model=WeatherOut)
def point_weather(lat: float, lon: float):
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise HTTPException(status_code=400, detail="Invalid coordinates")
    sample = weather_service.get_provider().get((lat, lon), utc_now().replace(microsecond=0))
    return _out(sample)


@router.get("/weather/voyage/{voyage_id}/track", response_model=RouteWeatherOut)
def voyage_track_weather(voyage_id: int, db: Session = Depends(get_db)):
    voyage = db.get(Voyage, voyage_id)
    if not voyage:
        raise HTTPException(status_code=404, detail=f"Voyage {voyage_id} not found")
    now = utc_now().replace(microsecond=0)
    origin, destination, _ = voyage_endpoints(voyage)
    route = generate_routes(origin, destination, voyage.vessel.design_speed_kn, now)[0]
    samples = weather_service.sample_along_route(
        route.waypoints, now, route.distance_nm / max(1.0, route.speed_kn), max_samples=8
    )
    aggregate = weather_service.aggregate(samples)
    return RouteWeatherOut(samples=[_out(s) for s in samples], **aggregate)
