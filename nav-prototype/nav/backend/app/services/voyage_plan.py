"""Voyage plan detail.

Three things the map and the voyage page need, all built from services that
already exist:

* ``leg_schedule``   - the passage broken into legs, each with the time the
                       vessel is expected there, the position, the distance,
                       the speed to hold and the fuel that leg burns.
* ``hazard_segments`` - stretches of the track where the forecast breaches a
                       heavy-weather threshold, with the window they fall in.
* ``wind_field``     - a coarse grid of wind arrows around the track, for the
                       weather overlay on the chart.

Nothing here invents a number. Every figure comes from the routing, weather
and fuel calculators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..config import AUXILIARY_FUEL_MT_PER_DAY
from .fuel import calculate_fuel, weather_factor
from .geo import Point, bearing_deg, haversine_nm
from .weather import WeatherSample, get_provider, heading_exposure, risk_index_for

# A leg is heavy weather if either of these is breached. Beaufort 8 is the
# usual point at which masters start altering course or slowing down.
GALE_WIND_KN = 34.0
HEAVY_SEA_M = 4.0
# Severe: storm force, or seas that stop a laden ship keeping schedule.
STORM_WIND_KN = 48.0
SEVERE_SEA_M = 6.0


@dataclass
class Leg:
    index: int
    start: Point
    end: Point
    depart_utc: datetime
    arrive_utc: datetime
    distance_nm: float
    speed_kn: float
    heading_deg: float
    fuel_mt: float
    wind_speed_kn: float
    wind_direction_deg: float
    wave_height_m: float
    wave_direction_deg: float
    current_speed_kn: float
    weather_source: str
    exposure: float  # 1.0 head sea, 0.0 following sea
    risk_index: float

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "start": [round(self.start[0], 4), round(self.start[1], 4)],
            "end": [round(self.end[0], 4), round(self.end[1], 4)],
            "depart_utc": self.depart_utc.isoformat(),
            "arrive_utc": self.arrive_utc.isoformat(),
            "distance_nm": round(self.distance_nm, 1),
            "speed_kn": round(self.speed_kn, 1),
            "heading_deg": round(self.heading_deg, 1),
            "fuel_mt": round(self.fuel_mt, 2),
            "wind_speed_kn": round(self.wind_speed_kn, 1),
            "wind_direction_deg": round(self.wind_direction_deg, 1),
            "wave_height_m": round(self.wave_height_m, 2),
            "wave_direction_deg": round(self.wave_direction_deg, 1),
            "current_speed_kn": round(self.current_speed_kn, 2),
            "weather_source": self.weather_source,
            "exposure": round(self.exposure, 3),
            "risk_index": round(self.risk_index, 4),
        }


@dataclass
class Hazard:
    severity: str  # "WATCH" | "DANGEROUS"
    reason: str
    start_utc: datetime
    end_utc: datetime
    max_wind_kn: float
    max_wave_m: float
    coordinates: list[Point] = field(default_factory=list)
    source: str = "MOCK"

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "reason": self.reason,
            "start_utc": self.start_utc.isoformat(),
            "end_utc": self.end_utc.isoformat(),
            "max_wind_kn": round(self.max_wind_kn, 1),
            "max_wave_m": round(self.max_wave_m, 2),
            "geometry": [[round(lon, 4), round(lat, 4)] for lat, lon in self.coordinates],
            "source": self.source,
        }


def _pick_evenly(points: list[Point], count: int) -> list[Point]:
    if len(points) <= count:
        return list(points)
    step = (len(points) - 1) / (count - 1)
    return [points[int(round(i * step))] for i in range(count)]


def leg_schedule(
    waypoints: list[Point],
    speed_kn: float,
    departure: datetime,
    vessel,
    max_legs: int = 12,
) -> list[Leg]:
    """Break the passage into legs and cost each one.

    The weather for a leg is sampled at the time the vessel is expected to be
    on it, not at departure, so a long passage shows conditions changing along
    the track.
    """
    nodes = _pick_evenly(waypoints, max_legs + 1)
    if len(nodes) < 2 or speed_kn <= 0:
        return []

    # Estimate each leg's timing first, then fetch all the weather at once.
    spans: list[tuple[Point, Point, float, datetime, datetime]] = []
    clock = departure
    for a, b in zip(nodes, nodes[1:]):
        distance = haversine_nm(a, b)
        hours = distance / speed_kn
        spans.append((a, b, distance, clock, clock + timedelta(hours=hours)))
        clock = clock + timedelta(hours=hours)

    midpoints = [
        ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b, _, _, _ in spans
    ]
    mid_times = [
        start + (end - start) / 2 for _, _, _, start, end in spans
    ]
    samples = get_provider().get_at_times(list(zip(midpoints, mid_times)))

    legs: list[Leg] = []
    for i, ((a, b, distance, start, end), sample) in enumerate(zip(spans, samples), start=1):
        heading = bearing_deg(a, b)
        hours = distance / speed_kn
        exposure = heading_exposure(heading, sample)
        fuel = calculate_fuel(
            base_daily_mt=vessel.base_consumption_mt_per_day,
            design_speed_kn=vessel.design_speed_kn,
            speed_kn=speed_kn,
            duration_hours=hours,
            weather_multiplier=weather_factor(
                sample.wave_height_m, sample.wind_speed_kn, exposure
            ),
            auxiliary_mt_per_day=AUXILIARY_FUEL_MT_PER_DAY,
        )
        legs.append(
            Leg(
                index=i,
                start=a,
                end=b,
                depart_utc=start,
                arrive_utc=end,
                distance_nm=distance,
                speed_kn=speed_kn,
                heading_deg=heading,
                fuel_mt=fuel.total_mt,
                wind_speed_kn=sample.wind_speed_kn,
                wind_direction_deg=sample.wind_direction_deg,
                wave_height_m=sample.wave_height_m,
                wave_direction_deg=sample.wave_direction_deg,
                current_speed_kn=sample.current_speed_kn,
                weather_source=sample.source,
                exposure=exposure,
                risk_index=risk_index_for(sample),
            )
        )
    return legs


def hazard_segments(legs: list[Leg]) -> list[Hazard]:
    """Merge consecutive heavy-weather legs into one warning each."""
    hazards: list[Hazard] = []
    current: list[Leg] = []

    def flush() -> None:
        if not current:
            return
        max_wind = max(l.wind_speed_kn for l in current)
        max_wave = max(l.wave_height_m for l in current)
        severe = max_wind >= STORM_WIND_KN or max_wave >= SEVERE_SEA_M
        reasons = []
        if max_wind >= GALE_WIND_KN:
            reasons.append(f"wind to {max_wind:.0f} kn")
        if max_wave >= HEAVY_SEA_M:
            reasons.append(f"seas to {max_wave:.1f} m")
        coordinates = [current[0].start] + [l.end for l in current]
        hazards.append(
            Hazard(
                severity="DANGEROUS" if severe else "WATCH",
                reason=" and ".join(reasons) or "heavy weather",
                start_utc=current[0].depart_utc,
                end_utc=current[-1].arrive_utc,
                max_wind_kn=max_wind,
                max_wave_m=max_wave,
                coordinates=coordinates,
                source=current[0].weather_source,
            )
        )
        current.clear()

    for leg in legs:
        if leg.wind_speed_kn >= GALE_WIND_KN or leg.wave_height_m >= HEAVY_SEA_M:
            current.append(leg)
        else:
            flush()
    flush()
    return hazards


def wind_field(
    waypoints: list[Point],
    valid_at: datetime,
    columns: int = 9,
    rows: int = 6,
    padding_deg: float = 6.0,
) -> list[WeatherSample]:
    """A coarse grid of wind and sea state around the track, for the overlay.

    One grid, one provider call. Kept small deliberately: this is a legibility
    aid on the chart, not a met product.
    """
    if not waypoints:
        return []
    lats = [p[0] for p in waypoints]
    lons = [p[1] for p in waypoints]
    lat0, lat1 = max(-80.0, min(lats) - padding_deg), min(80.0, max(lats) + padding_deg)
    lon0, lon1 = min(lons) - padding_deg, max(lons) + padding_deg

    points: list[Point] = []
    for r in range(rows):
        for c in range(columns):
            lat = lat0 + (lat1 - lat0) * (r / max(1, rows - 1))
            lon = lon0 + (lon1 - lon0) * (c / max(1, columns - 1))
            # Keep longitudes in range even when a track crosses the meridian.
            lon = ((lon + 180.0) % 360.0) - 180.0
            points.append((round(lat, 3), round(lon, 3)))

    return get_provider().get_at_times([(p, valid_at) for p in points])
