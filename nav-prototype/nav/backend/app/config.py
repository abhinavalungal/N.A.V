"""Central configuration for N.A.V.

Every tunable constant used by the deterministic calculation services lives
here so that the maths is auditable in one file instead of scattered around
the codebase.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# .env at the repo root wins, backend/.env is a convenience fallback.
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(PROJECT_DIR / ".env", override=True)


class Settings:
    """Runtime settings. Everything has a working default."""

    app_name = "N.A.V. — Nautical Agentic Navigator"
    api_prefix = "/api/v1"

    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'nav.db'}")

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "").strip()
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"

    # auto -> try Open-Meteo, fall back to mock. Other values: "mock", "open-meteo"
    weather_provider: str = os.getenv("WEATHER_PROVIDER", "auto").strip().lower()
    weather_timeout_s: float = float(os.getenv("WEATHER_TIMEOUT_SECONDS", "6"))

    cors_origins = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")
        if o.strip()
    ]

    @property
    def ai_mode(self) -> str:
        return "openai" if self.openai_api_key else "mock"


settings = Settings()


# ---------------------------------------------------------------------------
# Fuel & emissions constants
# ---------------------------------------------------------------------------

# CO2 emission factors in tonnes CO2 per tonne of fuel burned.
# Source: IMO MEPC.336(76) / EU MRV Regulation 2015/757 Annex I default factors.
EMISSION_FACTORS: dict[str, float] = {
    "HSFO": 3.114,  # heavy fuel oil
    "VLSFO": 3.151,  # treated as light fuel oil
    "LFO": 3.151,
    "MGO": 3.206,
    "MDO": 3.206,
    "LNG": 2.750,
}

# Lower calorific value (MJ/kg) and sulphur limit, used for reporting only.
FUEL_PROPERTIES: dict[str, dict[str, float | str]] = {
    "HSFO": {"lcv_mj_per_kg": 40.2, "sulphur_pct": 2.5, "label": "Heavy fuel oil"},
    "VLSFO": {"lcv_mj_per_kg": 41.0, "sulphur_pct": 0.5, "label": "Very low sulphur fuel oil"},
    "LFO": {"lcv_mj_per_kg": 41.0, "sulphur_pct": 0.5, "label": "Light fuel oil"},
    "MGO": {"lcv_mj_per_kg": 42.7, "sulphur_pct": 0.1, "label": "Marine gas oil"},
    "MDO": {"lcv_mj_per_kg": 42.7, "sulphur_pct": 0.1, "label": "Marine diesel oil"},
    "LNG": {"lcv_mj_per_kg": 48.0, "sulphur_pct": 0.0, "label": "Liquefied natural gas"},
}

DEFAULT_FUEL_TYPE = "VLSFO"

# Auxiliary engine + boiler load, tonnes/day, added on top of propulsion fuel.
AUXILIARY_FUEL_MT_PER_DAY = 2.4

# Propulsion follows the admiralty cube law: consumption scales with speed^3.
SPEED_EXPONENT = 3.0

# --- Weather resistance heuristic -----------------------------------------
# Prototype approximation, not a validated ship resistance model. Tunable here.
WAVE_PENALTY_COEFF = 0.045  # applied to significant wave height ** 1.5
WAVE_PENALTY_EXPONENT = 1.5
WIND_PENALTY_COEFF = 0.006  # per knot of wind above the threshold
WIND_PENALTY_THRESHOLD_KN = 12.0
MAX_WEATHER_FACTOR = 1.60  # cap so a storm cannot produce absurd numbers
HEADING_PENALTY_HEAD_SEA = 1.0  # multiplier when weather is on the bow
HEADING_PENALTY_FOLLOWING = 0.35  # multiplier when weather is astern

# Ocean current is applied to speed over ground, not to fuel.
MAX_CURRENT_EFFECT_KN = 2.0


# ---------------------------------------------------------------------------
# Weather risk banding
# ---------------------------------------------------------------------------
# Risk index is 0..1. Bands are inclusive of the upper bound.
RISK_BANDS: list[tuple[float, str]] = [
    (0.15, "VERY_LOW"),
    (0.32, "LOW"),
    (0.55, "MODERATE"),
    (0.75, "HIGH"),
    (1.01, "SEVERE"),
]
RISK_ORDER = ["VERY_LOW", "LOW", "MODERATE", "HIGH", "SEVERE"]


# ---------------------------------------------------------------------------
# Optimizer
# ---------------------------------------------------------------------------
OBJECTIVES = ["MIN_FUEL", "FASTEST", "MIN_EMISSIONS", "BALANCED"]

# score = w_fuel*n_fuel + w_eta*n_eta + w_co2*n_co2 + w_risk*n_risk  (lower wins)
OBJECTIVE_WEIGHTS: dict[str, dict[str, float]] = {
    "MIN_FUEL": {"fuel": 0.70, "eta": 0.10, "co2": 0.10, "risk": 0.10},
    "FASTEST": {"fuel": 0.10, "eta": 0.70, "co2": 0.05, "risk": 0.15},
    "MIN_EMISSIONS": {"fuel": 0.15, "eta": 0.10, "co2": 0.65, "risk": 0.10},
    "BALANCED": {"fuel": 0.35, "eta": 0.30, "co2": 0.20, "risk": 0.15},
}

OBJECTIVE_LABELS = {
    "MIN_FUEL": "Minimum fuel",
    "FASTEST": "Fastest arrival",
    "MIN_EMISSIONS": "Minimum emissions",
    "BALANCED": "Balanced",
}

# Speed offsets applied to each generated route variant, as a fraction of the
# vessel design speed.
ROUTE_VARIANTS: dict[str, dict[str, float | str]] = {
    "FASTEST": {"label": "Fastest", "speed_factor": 1.00},
    "FUEL_EFFICIENT": {"label": "Fuel efficient", "speed_factor": 0.88},
    "WEATHER_OPTIMIZED": {"label": "Weather optimized", "speed_factor": 0.94},
    "ECO_SLOW_STEAM": {"label": "Eco slow steam", "speed_factor": 0.80},
}

# Port time / manoeuvring allowance added to every voyage duration, hours.
PORT_ALLOWANCE_HOURS = 6.0
