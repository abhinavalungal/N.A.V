"""Create a populated demo database.

    python seed.py             # rebuild data/nav.db from scratch
    python seed.py --keep      # keep the existing data and top it up
    python seed.py --if-empty  # seed only when the database has no vessels
                               # (safe to run on every deploy)

All figures are labelled DEMO. They are plausible operating values for the
vessel classes involved, not measurements from real ships.
"""

from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta

from app.clock import utc_now
from app.config import DATA_DIR, settings
from app.database import Base, SessionLocal, engine
from app.models import (
    Company,
    FuelPrice,
    HistoricalVoyage,
    Vessel,
    VesselPosition,
    Voyage,
    WeatherRecord,
)
from app.services import weather as weather_service
from app.services.emissions import calculate_emissions
from app.services.eta import calculate_eta
from app.services.fuel import calculate_fuel
from app.services.geo import bearing_deg, position_along_path
from app.services.optimizer import Constraints, run_optimization
from app.services.routing import sea_route

# Seeding always uses the deterministic mock weather field so the demo
# database is reproducible and the script never depends on the network.
weather_service._provider = weather_service.MockWeatherProvider()

RNG = random.Random(7)
NOW = utc_now().replace(minute=0, second=0, microsecond=0)

COMPANIES = [
    ("Southgate Tankers", "Singapore", "Tankers"),
    ("Meridian Bulk Carriers", "Greece", "Dry bulk"),
    ("Blue Horizon Shipping", "Denmark", "Container"),
    ("Auralite Gas Transport", "Japan", "Gas"),
    ("Northwind Maritime", "United Kingdom", "Mixed fleet"),
]

# (name, imo, type, company index, dwt, design speed, fuel, MT/day at design speed, year)
VESSELS = [
    ("STI Alpha", "9741001", "Product tanker", 0, 49_999, 14.5, "VLSFO", 26.0, 2016),
    ("STI Bravo", "9741002", "Product tanker", 0, 49_700, 14.2, "VLSFO", 25.5, 2017),
    ("STI Charlie", "9741003", "Chemical tanker", 0, 37_000, 14.0, "MGO", 22.0, 2019),
    ("Ocean Navigator", "9612004", "Capesize bulk carrier", 1, 180_000, 14.0, "HSFO", 42.0, 2014),
    ("Pacific Trader", "9612005", "Panamax bulk carrier", 1, 82_000, 13.8, "VLSFO", 30.0, 2015),
    ("Baltic Harrier", "9612006", "Handysize bulk carrier", 1, 38_000, 13.5, "VLSFO", 20.0, 2018),
    ("Coral Meridian", "9832007", "Container feeder", 2, 25_000, 18.0, "VLSFO", 48.0, 2020),
    ("Atlantic Sentinel", "9832008", "Container vessel", 2, 68_000, 19.5, "VLSFO", 78.0, 2021),
    ("Nordic Falcon", "9905009", "LNG carrier", 3, 95_000, 19.0, "LNG", 95.0, 2022),
    ("Aurora Meridian", "9741010", "Aframax tanker", 4, 115_000, 14.6, "HSFO", 38.0, 2013),
]

LANES = {
    "tanker": [
        ("Ras Tanura", "Rotterdam"),
        ("Fujairah", "Singapore"),
        ("Jebel Ali", "Mumbai"),
        ("Houston", "Rotterdam"),
        ("Singapore", "Yokohama"),
        ("Ras Tanura", "Yokohama"),
    ],
    "bulk": [
        ("Dampier", "Qingdao"),
        ("Santos", "Qingdao"),
        ("Durban", "Mumbai"),
        ("Houston", "Shanghai"),
        ("Santos", "Rotterdam"),
        ("Dampier", "Ningbo"),
    ],
    "container": [
        ("Singapore", "Rotterdam"),
        ("Shanghai", "Los Angeles"),
        ("Busan", "Los Angeles"),
        ("Ningbo", "Singapore"),
        ("Antwerp", "New York"),
    ],
    "gas": [
        ("Ras Tanura", "Yokohama"),
        ("Houston", "Rotterdam"),
        ("Fujairah", "Busan"),
    ],
}

CARGO = {
    "tanker": "Crude / products",
    "bulk": "Iron ore / grain",
    "container": "Containers",
    "gas": "LNG",
}


def segment_of(vessel_type: str) -> str:
    t = vessel_type.lower()
    if "tanker" in t:
        return "tanker"
    if "bulk" in t:
        return "bulk"
    if "container" in t:
        return "container"
    return "gas"


def build_voyage(
    vessel: Vessel,
    origin: str,
    destination: str,
    departure: datetime,
    status: str,
    index: int,
    progress: float = 0.0,
    speed_bias: float = 1.0,
) -> Voyage:
    """speed_bias < 1 means the vessel is currently running behind the plan."""
    points, _via, distance = sea_route(origin, destination)
    speed = round(vessel.design_speed_kn * 0.92, 1)
    eta = calculate_eta(distance, speed, departure)
    planned = calculate_fuel(
        base_daily_mt=vessel.base_consumption_mt_per_day,
        design_speed_kn=vessel.design_speed_kn,
        speed_kn=speed,
        duration_hours=eta.sea_hours,
        weather_multiplier=1.08,  # planning allowance
    )

    sailed = distance * progress
    remaining = max(0.0, distance - sailed)
    if status == "ACTIVE":
        position = position_along_path(points, sailed)
        current_speed = round(speed * RNG.uniform(0.90, 1.03) * speed_bias, 1)
        consumed = round(planned.total_mt * progress * RNG.uniform(0.97, 1.12), 1)
    elif status == "COMPLETED":
        position = points[-1]
        current_speed = 0.0
        consumed = round(planned.total_mt * RNG.uniform(0.96, 1.10), 1)
        remaining = 0.0
    else:
        position = points[0]
        current_speed = 0.0
        consumed = 0.0

    reference = f"{''.join(w[0] for w in vessel.name.split()[:2]).upper()}-{departure:%Y}-{index:03d}"
    return Voyage(
        reference=reference,
        vessel_id=vessel.id,
        origin_port=origin,
        origin_lat=points[0][0],
        origin_lon=points[0][1],
        destination_port=destination,
        destination_lat=points[-1][0],
        destination_lon=points[-1][1],
        departure_utc=departure,
        expected_arrival_utc=eta.eta_utc,
        required_arrival_utc=eta.eta_utc + timedelta(hours=RNG.choice([12, 24, 36, 48])),
        current_lat=round(position[0], 4),
        current_lon=round(position[1], 4),
        current_speed_kn=current_speed,
        planned_speed_kn=speed,
        distance_nm=round(distance, 1),
        distance_remaining_nm=round(remaining, 1),
        planned_fuel_mt=planned.total_mt,
        consumed_fuel_mt=consumed,
        cargo_t=round(vessel.deadweight_t * RNG.uniform(0.72, 0.95), 0),
        status=status,
    )


def seed(reset: bool = True) -> None:
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    companies = [Company(name=n, country=c, fleet_segment=s) for n, c, s in COMPANIES]
    db.add_all(companies)
    db.flush()

    vessels: list[Vessel] = []
    for name, imo, vtype, company_ix, dwt, speed, fuel, cons, year in VESSELS:
        vessels.append(
            Vessel(
                imo=imo,
                name=name,
                vessel_type=vtype,
                company_id=companies[company_ix].id,
                deadweight_t=dwt,
                design_speed_kn=speed,
                current_speed_kn=0.0,
                fuel_type=fuel,
                base_consumption_mt_per_day=cons,
                latitude=0.0,
                longitude=0.0,
                heading_deg=0.0,
                status="AT_SEA",
                year_built=year,
                data_source="DEMO",
            )
        )
    db.add_all(vessels)
    db.flush()

    voyage_index: dict[int, int] = {}
    all_voyages: list[Voyage] = []

    # One active voyage per vessel, at different stages of the passage.
    for i, vessel in enumerate(vessels):
        segment = segment_of(vessel.vessel_type)
        origin, destination = LANES[segment][i % len(LANES[segment])]
        progress = [0.62, 0.28, 0.44, 0.71, 0.15, 0.55, 0.36, 0.80, 0.22, 0.48][i]
        # Two vessels are deliberately running slow so the alert rules fire.
        bias = 0.80 if i in (3, 7) else 1.0
        points, _via, distance = sea_route(origin, destination)
        speed = vessel.design_speed_kn * 0.92
        hours_elapsed = (distance * progress) / speed
        departure = NOW - timedelta(hours=round(hours_elapsed, 1))
        voyage_index[vessel.id] = voyage_index.get(vessel.id, 0) + 1
        voyage = build_voyage(
            vessel, origin, destination, departure, "ACTIVE", voyage_index[vessel.id],
            progress=progress, speed_bias=bias,
        )
        db.add(voyage)
        db.flush()
        all_voyages.append(voyage)

        vessel.latitude = voyage.current_lat
        vessel.longitude = voyage.current_lon
        vessel.current_speed_kn = voyage.current_speed_kn
        vessel.heading_deg = round(
            bearing_deg((voyage.current_lat, voyage.current_lon), points[-1]), 1
        )

        # 24 hours of hourly positions behind the vessel.
        sailed = distance * progress
        for h in range(24, 0, -2):
            back = max(0.0, sailed - voyage.current_speed_kn * h)
            p = position_along_path(points, back)
            db.add(
                VesselPosition(
                    vessel_id=vessel.id,
                    voyage_id=voyage.id,
                    latitude=round(p[0], 4),
                    longitude=round(p[1], 4),
                    speed_kn=round(voyage.current_speed_kn * RNG.uniform(0.96, 1.04), 1),
                    heading_deg=vessel.heading_deg,
                    recorded_at=NOW - timedelta(hours=h),
                )
            )

    # Planned voyages.
    for i, vessel in enumerate(vessels[:7]):
        segment = segment_of(vessel.vessel_type)
        origin, destination = LANES[segment][(i + 2) % len(LANES[segment])]
        voyage_index[vessel.id] = voyage_index.get(vessel.id, 0) + 1
        voyage = build_voyage(
            vessel,
            origin,
            destination,
            NOW + timedelta(days=RNG.randint(3, 21)),
            "PLANNED",
            voyage_index[vessel.id],
        )
        db.add(voyage)
        db.flush()
        all_voyages.append(voyage)

    # Completed voyages.
    for i, vessel in enumerate(vessels[:6]):
        segment = segment_of(vessel.vessel_type)
        origin, destination = LANES[segment][(i + 1) % len(LANES[segment])]
        voyage_index[vessel.id] = voyage_index.get(vessel.id, 0) + 1
        voyage = build_voyage(
            vessel,
            origin,
            destination,
            NOW - timedelta(days=RNG.randint(40, 90)),
            "COMPLETED",
            voyage_index[vessel.id],
            progress=1.0,
        )
        db.add(voyage)
        db.flush()
        all_voyages.append(voyage)

    # Historical voyages: six per vessel, with actuals drifting off plan.
    for vessel in vessels:
        segment = segment_of(vessel.vessel_type)
        for n in range(6):
            origin, destination = LANES[segment][(n + 3) % len(LANES[segment])]
            _points, _via, distance = sea_route(origin, destination)
            speed = round(vessel.design_speed_kn * RNG.uniform(0.85, 0.98), 2)
            eta = calculate_eta(distance, speed, NOW)
            predicted = calculate_fuel(
                base_daily_mt=vessel.base_consumption_mt_per_day,
                design_speed_kn=vessel.design_speed_kn,
                speed_kn=speed,
                duration_hours=eta.sea_hours,
                weather_multiplier=1.05,
            )
            fuel_variance = RNG.uniform(-0.04, 0.13)
            time_variance = RNG.uniform(-0.03, 0.10)
            actual_fuel = round(predicted.total_mt * (1 + fuel_variance), 1)
            actual_hours = round(eta.duration_hours * (1 + time_variance), 1)
            departure = NOW - timedelta(days=30 * (n + 1) + RNG.randint(0, 9))
            db.add(
                HistoricalVoyage(
                    vessel_id=vessel.id,
                    reference=f"{''.join(w[0] for w in vessel.name.split()[:2]).upper()}-H{n + 1:02d}",
                    origin_port=origin,
                    destination_port=destination,
                    departure_utc=departure,
                    arrival_utc=departure + timedelta(hours=actual_hours),
                    distance_nm=round(distance, 1),
                    average_speed_kn=round(distance / max(1.0, actual_hours - 6), 2),
                    predicted_fuel_mt=predicted.total_mt,
                    actual_fuel_mt=actual_fuel,
                    predicted_duration_hours=eta.duration_hours,
                    actual_duration_hours=actual_hours,
                    co2_mt=calculate_emissions(actual_fuel, vessel.fuel_type).co2_mt,
                    fuel_type=vessel.fuel_type,
                    data_source="DEMO",
                )
            )

    # Weather snapshots at each vessel position.
    provider = weather_service.get_provider()
    for vessel in vessels:
        s = provider.get((vessel.latitude, vessel.longitude), NOW)
        db.add(
            WeatherRecord(
                latitude=s.latitude,
                longitude=s.longitude,
                valid_at=s.valid_at,
                wind_speed_kn=s.wind_speed_kn,
                wind_direction_deg=s.wind_direction_deg,
                wave_height_m=s.wave_height_m,
                wave_direction_deg=s.wave_direction_deg,
                current_speed_kn=s.current_speed_kn,
                current_direction_deg=s.current_direction_deg,
                visibility_nm=s.visibility_nm,
                temperature_c=s.temperature_c,
                source=s.source,
            )
        )

    # Indicative bunker prices, clearly marked as demo values.
    base_prices = {"VLSFO": 610.0, "HSFO": 470.0, "MGO": 780.0, "LNG": 540.0}
    for port in ("Singapore", "Rotterdam", "Fujairah", "Houston", "Busan"):
        for fuel_type, price in base_prices.items():
            db.add(
                FuelPrice(
                    port=port,
                    fuel_type=fuel_type,
                    price_usd_per_mt=round(price * RNG.uniform(0.95, 1.06), 1),
                    quoted_at=NOW,
                    source="DEMO",
                )
            )

    db.commit()

    # Pre-run the optimizer on five active voyages so the dashboard opens with
    # real pending recommendations rather than empty state.
    active = [v for v in all_voyages if v.status == "ACTIVE"][:5]
    for voyage in active:
        run_optimization(db, voyage, "BALANCED", Constraints())

    db.commit()

    counts = {
        "companies": db.query(Company).count(),
        "vessels": db.query(Vessel).count(),
        "voyages": db.query(Voyage).count(),
        "positions": db.query(VesselPosition).count(),
        "historical_voyages": db.query(HistoricalVoyage).count(),
        "fuel_prices": db.query(FuelPrice).count(),
    }
    db.close()

    print(f"Database: {settings.database_url}")
    print(f"Data directory: {DATA_DIR}")
    for key, value in counts.items():
        print(f"  {key:<20} {value}")
    print("Seeded 5 pending N.A.V. recommendations from real optimizer runs.")


def _already_seeded() -> bool:
    """True when a database is present and already holds a fleet."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        return db.query(Vessel).count() > 0
    finally:
        db.close()


if __name__ == "__main__":
    if "--if-empty" in sys.argv:
        if _already_seeded():
            print("Database already seeded, leaving it alone.")
            sys.exit(0)
        seed(reset=False)
    else:
        seed(reset="--keep" not in sys.argv)
