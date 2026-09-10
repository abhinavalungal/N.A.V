from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..clock import utc_now
from ..database import get_db
from ..models import FuelPrice, Vessel
from ..schemas import FuelPriceOut, FuelRequest, FuelResponse
from ..services.emissions import calculate_emissions, fuel_catalogue
from ..services.eta import calculate_eta
from ..services.fuel import calculate_fuel, weather_factor

router = APIRouter(tags=["fuel"])


@router.post("/fuel/calculate", response_model=FuelResponse)
def fuel_calculate(payload: FuelRequest, db: Session = Depends(get_db)):
    vessel = db.get(Vessel, payload.vessel_id)
    if not vessel:
        raise HTTPException(status_code=404, detail=f"Vessel {payload.vessel_id} not found")

    wf = weather_factor(payload.wave_height_m, payload.wind_speed_kn)
    eta = calculate_eta(payload.distance_nm, payload.speed_kn, utc_now())
    fuel = calculate_fuel(
        base_daily_mt=vessel.base_consumption_mt_per_day,
        design_speed_kn=vessel.design_speed_kn,
        speed_kn=payload.speed_kn,
        duration_hours=eta.sea_hours,
        weather_multiplier=wf,
    )
    emissions = calculate_emissions(
        fuel.total_mt, vessel.fuel_type, payload.distance_nm, vessel.deadweight_t
    )
    return FuelResponse(
        vessel_id=vessel.id,
        distance_nm=payload.distance_nm,
        speed_kn=payload.speed_kn,
        duration_hours=eta.duration_hours,
        fuel_mt=fuel.total_mt,
        co2_mt=emissions.co2_mt,
        daily_consumption_mt=fuel.daily_mt,
        speed_factor=fuel.speed_factor,
        weather_factor=fuel.weather_factor,
        fuel_type=emissions.fuel_type,
        emission_factor=emissions.emission_factor,
    )


@router.get("/fuel/prices", response_model=list[FuelPriceOut])
def fuel_prices(db: Session = Depends(get_db)):
    return db.query(FuelPrice).order_by(desc(FuelPrice.quoted_at), FuelPrice.port).limit(60).all()


@router.get("/fuel/types")
def fuel_types():
    return fuel_catalogue()
