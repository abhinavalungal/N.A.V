"""Deterministic fuel consumption.

    fuel = base_daily_consumption x voyage_days x speed_factor x weather_factor
           + auxiliary load

No LLM ever touches these numbers.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import (
    AUXILIARY_FUEL_MT_PER_DAY,
    HEADING_PENALTY_FOLLOWING,
    HEADING_PENALTY_HEAD_SEA,
    MAX_WEATHER_FACTOR,
    SPEED_EXPONENT,
    WAVE_PENALTY_COEFF,
    WAVE_PENALTY_EXPONENT,
    WIND_PENALTY_COEFF,
    WIND_PENALTY_THRESHOLD_KN,
)


@dataclass
class FuelResult:
    total_mt: float
    propulsion_mt: float
    auxiliary_mt: float
    daily_mt: float
    speed_factor: float
    weather_factor: float
    days: float

    def to_dict(self) -> dict:
        return {
            "total_mt": self.total_mt,
            "propulsion_mt": self.propulsion_mt,
            "auxiliary_mt": self.auxiliary_mt,
            "daily_mt": self.daily_mt,
            "speed_factor": self.speed_factor,
            "weather_factor": self.weather_factor,
            "days": self.days,
        }


def speed_factor(speed_kn: float, design_speed_kn: float) -> float:
    """Admiralty cube law: propulsion power scales with speed^3."""
    if design_speed_kn <= 0:
        raise ValueError("design_speed_kn must be positive")
    if speed_kn <= 0:
        raise ValueError("speed_kn must be positive")
    return round((speed_kn / design_speed_kn) ** SPEED_EXPONENT, 6)


def weather_factor(
    wave_height_m: float,
    wind_speed_kn: float,
    head_sea_exposure: float = 0.7,
) -> float:
    """Added resistance multiplier.

    `head_sea_exposure` is 1.0 for a head sea and 0.0 for a following sea.
    This is a tunable prototype heuristic, not a validated resistance model;
    all coefficients live in config.py.
    """
    exposure = max(0.0, min(1.0, head_sea_exposure))
    directional = HEADING_PENALTY_FOLLOWING + (
        HEADING_PENALTY_HEAD_SEA - HEADING_PENALTY_FOLLOWING
    ) * exposure
    wave_term = WAVE_PENALTY_COEFF * max(0.0, wave_height_m) ** WAVE_PENALTY_EXPONENT
    wind_term = WIND_PENALTY_COEFF * max(0.0, wind_speed_kn - WIND_PENALTY_THRESHOLD_KN)
    return round(min(MAX_WEATHER_FACTOR, 1.0 + directional * (wave_term + wind_term)), 4)


def calculate_fuel(
    base_daily_mt: float,
    design_speed_kn: float,
    speed_kn: float,
    duration_hours: float,
    weather_multiplier: float = 1.0,
    auxiliary_mt_per_day: float = AUXILIARY_FUEL_MT_PER_DAY,
) -> FuelResult:
    if base_daily_mt <= 0:
        raise ValueError("base_daily_mt must be positive")
    if duration_hours < 0:
        raise ValueError("duration_hours cannot be negative")

    days = duration_hours / 24.0
    sf = speed_factor(speed_kn, design_speed_kn)
    daily = base_daily_mt * sf * weather_multiplier
    propulsion = daily * days
    auxiliary = auxiliary_mt_per_day * days
    return FuelResult(
        total_mt=round(propulsion + auxiliary, 2),
        propulsion_mt=round(propulsion, 2),
        auxiliary_mt=round(auxiliary, 2),
        daily_mt=round(daily + auxiliary_mt_per_day, 2),
        speed_factor=sf,
        weather_factor=round(weather_multiplier, 4),
        days=round(days, 3),
    )


def fuel_cost_usd(fuel_mt: float, price_usd_per_mt: float) -> float:
    return round(fuel_mt * price_usd_per_mt, 2)
