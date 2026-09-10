"""Deterministic emissions.

    CO2 = fuel_consumed x emission_factor

Emission factors are the IMO / EU MRV defaults and live in config.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import DEFAULT_FUEL_TYPE, EMISSION_FACTORS, FUEL_PROPERTIES


class UnknownFuelType(ValueError):
    pass


@dataclass
class EmissionsResult:
    co2_mt: float
    fuel_type: str
    emission_factor: float
    co2_per_nm_kg: float | None
    aer_g_per_dwt_nm: float | None

    def to_dict(self) -> dict:
        return {
            "co2_mt": self.co2_mt,
            "fuel_type": self.fuel_type,
            "emission_factor": self.emission_factor,
            "co2_per_nm_kg": self.co2_per_nm_kg,
            "aer_g_per_dwt_nm": self.aer_g_per_dwt_nm,
        }


def emission_factor(fuel_type: str) -> float:
    key = (fuel_type or DEFAULT_FUEL_TYPE).upper()
    if key not in EMISSION_FACTORS:
        raise UnknownFuelType(
            f"Unknown fuel type '{fuel_type}'. Known: {', '.join(sorted(EMISSION_FACTORS))}"
        )
    return EMISSION_FACTORS[key]


def calculate_emissions(
    fuel_mt: float,
    fuel_type: str = DEFAULT_FUEL_TYPE,
    distance_nm: float | None = None,
    deadweight_t: float | None = None,
) -> EmissionsResult:
    if fuel_mt < 0:
        raise ValueError("fuel_mt cannot be negative")
    factor = emission_factor(fuel_type)
    co2 = fuel_mt * factor
    per_nm = round(co2 * 1000.0 / distance_nm, 2) if distance_nm else None
    # AER: annual efficiency ratio style intensity, gCO2 per dwt-nautical mile.
    aer = (
        round(co2 * 1_000_000.0 / (deadweight_t * distance_nm), 3)
        if distance_nm and deadweight_t
        else None
    )
    return EmissionsResult(
        co2_mt=round(co2, 2),
        fuel_type=(fuel_type or DEFAULT_FUEL_TYPE).upper(),
        emission_factor=factor,
        co2_per_nm_kg=per_nm,
        aer_g_per_dwt_nm=aer,
    )


def fuel_catalogue() -> list[dict]:
    return [
        {
            "fuel_type": key,
            "label": FUEL_PROPERTIES[key]["label"],
            "emission_factor": EMISSION_FACTORS[key],
            "sulphur_pct": FUEL_PROPERTIES[key]["sulphur_pct"],
            "lcv_mj_per_kg": FUEL_PROPERTIES[key]["lcv_mj_per_kg"],
        }
        for key in EMISSION_FACTORS
    ]
