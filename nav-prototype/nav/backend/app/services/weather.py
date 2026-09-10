"""Weather service.

Two providers behind one interface:

* MockWeatherProvider  - deterministic synthetic field, always available.
* OpenMeteoWeatherProvider - free Open-Meteo marine + forecast APIs, no key.

Every sample carries `source`, and the API/UI always show it. Mock data is
never presented as live data.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

from ..config import RISK_BANDS, settings
from .geo import Point, relative_angle

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


@dataclass
class WeatherSample:
    latitude: float
    longitude: float
    valid_at: datetime
    wind_speed_kn: float
    wind_direction_deg: float
    wave_height_m: float
    wave_direction_deg: float
    current_speed_kn: float
    current_direction_deg: float
    visibility_nm: float
    temperature_c: float
    source: str  # "MOCK" | "OPEN_METEO"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["valid_at"] = self.valid_at.isoformat()
        return d


def risk_band(index: float) -> str:
    for threshold, label in RISK_BANDS:
        if index <= threshold:
            return label
    return "SEVERE"


def risk_index_for(sample: WeatherSample) -> float:
    """0..1 risk index built from wave height, wind and visibility."""
    wave = min(1.0, sample.wave_height_m / 7.0)
    wind = min(1.0, max(0.0, sample.wind_speed_kn - 8.0) / 42.0)
    vis = min(1.0, max(0.0, 6.0 - sample.visibility_nm) / 6.0)
    return round(min(1.0, 0.6 * wave + 0.32 * wind + 0.08 * vis), 4)


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


class WeatherProvider:
    name = "BASE"

    def get_many(self, points: list[Point], valid_at: datetime) -> list[WeatherSample]:
        raise NotImplementedError

    def get(self, point: Point, valid_at: datetime | None = None) -> WeatherSample:
        valid_at = valid_at or datetime.now(timezone.utc).replace(tzinfo=None)
        return self.get_many([point], valid_at)[0]


class MockWeatherProvider(WeatherProvider):
    """Smooth, deterministic pseudo-weather.

    Wave height uses the Pierson-Moskowitz fully developed sea relation
    Hs = 0.0246 * U^2 (U in m/s) so wind and sea state stay consistent.
    """

    name = "MOCK"

    def _field(self, lat: float, lon: float, hours: float, phase: float) -> float:
        a = math.sin(math.radians(lat * 2.3) + hours / 37.0 + phase)
        b = math.cos(math.radians(lon * 1.6) + hours / 53.0 + phase * 1.7)
        c = math.sin(math.radians((lat + lon) * 0.9) + phase * 0.5)
        return (a * 0.5 + b * 0.35 + c * 0.15)  # -1..1

    def get_many(self, points: list[Point], valid_at: datetime) -> list[WeatherSample]:
        hours = valid_at.timestamp() / 3600.0
        out: list[WeatherSample] = []
        for lat, lon in points:
            # Storm belts around 40-55 degrees north and south.
            belt = 1.0 + 1.35 * math.exp(-(((abs(lat) - 47.0) / 13.0) ** 2))
            tropics = 1.0 + 0.25 * math.exp(-((lat / 9.0) ** 2))
            raw = self._field(lat, lon, hours, 0.0)
            wind = max(3.0, min(52.0, (7.0 + 13.0 * (0.5 + 0.5 * raw)) * belt * tropics))
            u_ms = wind * 0.514444
            swell = 0.85 + 0.35 * (0.5 + 0.5 * self._field(lat, lon, hours, 2.1))
            wave = max(0.2, min(9.0, 0.0246 * u_ms**2 * swell))
            wind_dir = (180.0 + 180.0 * self._field(lat, lon, hours, 1.1)) % 360.0
            wave_dir = (wind_dir + 18.0 * self._field(lat, lon, hours, 3.3)) % 360.0
            current = max(0.05, min(2.4, 0.6 + 0.8 * self._field(lat, lon, hours, 4.7)))
            current_dir = (200.0 + 160.0 * self._field(lat, lon, hours, 5.9)) % 360.0
            vis = max(0.6, min(12.0, 9.0 + 3.0 * self._field(lat, lon, hours, 6.5) - wave * 0.4))
            temp = 29.0 - 0.42 * abs(lat) + 2.5 * self._field(lat, lon, hours, 7.2)
            out.append(
                WeatherSample(
                    latitude=round(lat, 4),
                    longitude=round(lon, 4),
                    valid_at=valid_at,
                    wind_speed_kn=round(wind, 1),
                    wind_direction_deg=round(wind_dir, 1),
                    wave_height_m=round(wave, 2),
                    wave_direction_deg=round(wave_dir, 1),
                    current_speed_kn=round(current, 2),
                    current_direction_deg=round(current_dir, 1),
                    visibility_nm=round(vis, 1),
                    temperature_c=round(temp, 1),
                    source=self.name,
                )
            )
        return out


class OpenMeteoWeatherProvider(WeatherProvider):
    """Live weather from Open-Meteo (free, no API key, no registration).

    Any failure - network down, rate limited, date outside forecast range -
    degrades to the mock provider for the affected points, and the sample
    source says so.
    """

    name = "OPEN_METEO"

    def __init__(self, fallback: WeatherProvider, timeout: float | None = None):
        self.fallback = fallback
        self.timeout = timeout or settings.weather_timeout_s
        self._cache: dict[tuple, WeatherSample] = {}

    @staticmethod
    def _key(point: Point, valid_at: datetime) -> tuple:
        return (round(point[0], 1), round(point[1], 1), valid_at.strftime("%Y-%m-%dT%H"))

    def get_many(self, points: list[Point], valid_at: datetime) -> list[WeatherSample]:
        import httpx  # local import keeps the module importable without httpx

        results: dict[int, WeatherSample] = {}
        pending: list[int] = []
        for i, p in enumerate(points):
            cached = self._cache.get(self._key(p, valid_at))
            if cached:
                results[i] = cached
            else:
                pending.append(i)

        if pending:
            # Open-Meteo forecast covers roughly -3 months to +16 days; marine
            # is shorter. Outside that window there is nothing to fetch.
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            in_range = timedelta(days=-90) <= (valid_at - now) <= timedelta(days=7)
            fetched: dict[int, WeatherSample] = {}
            if in_range:
                try:
                    fetched = self._fetch(httpx, [points[i] for i in pending], valid_at, pending)
                except Exception:  # noqa: BLE001 - any failure degrades to mock
                    fetched = {}
            for i, sample in fetched.items():
                self._cache[self._key(points[i], valid_at)] = sample
                results[i] = sample
            missing = [i for i in pending if i not in results]
            if missing:
                for i, sample in zip(missing, self.fallback.get_many([points[i] for i in missing], valid_at)):
                    results[i] = sample

        return [results[i] for i in range(len(points))]

    def _fetch(self, httpx, points: list[Point], valid_at: datetime, idx: list[int]) -> dict:
        lats = ",".join(f"{p[0]:.3f}" for p in points)
        lons = ",".join(f"{p[1]:.3f}" for p in points)
        day = valid_at.strftime("%Y-%m-%d")
        common = {
            "latitude": lats,
            "longitude": lons,
            "start_date": day,
            "end_date": day,
            "timezone": "UTC",
        }
        with httpx.Client(timeout=self.timeout) as client:
            marine = client.get(
                MARINE_URL,
                params={
                    **common,
                    "hourly": "wave_height,wave_direction,ocean_current_velocity,ocean_current_direction",
                },
            )
            marine.raise_for_status()
            atmos = client.get(
                FORECAST_URL,
                params={
                    **common,
                    "hourly": "wind_speed_10m,wind_direction_10m,visibility,temperature_2m",
                    "wind_speed_unit": "kn",
                },
            )
            atmos.raise_for_status()

        marine_series = _as_list(marine.json())
        atmos_series = _as_list(atmos.json())
        if len(marine_series) != len(points) or len(atmos_series) != len(points):
            raise ValueError("Open-Meteo returned an unexpected number of locations")

        hour = valid_at.hour
        out: dict[int, WeatherSample] = {}
        for n, (point, m, a) in enumerate(zip(points, marine_series, atmos_series)):
            mh, ah = m.get("hourly", {}), a.get("hourly", {})
            wave = _pick(mh.get("wave_height"), hour)
            wind = _pick(ah.get("wind_speed_10m"), hour)
            if wave is None or wind is None:
                continue  # open sea point with no marine data -> caller falls back
            vis_m = _pick(ah.get("visibility"), hour)
            out[idx[n]] = WeatherSample(
                latitude=round(point[0], 4),
                longitude=round(point[1], 4),
                valid_at=valid_at,
                wind_speed_kn=round(float(wind), 1),
                wind_direction_deg=round(float(_pick(ah.get("wind_direction_10m"), hour) or 0.0), 1),
                wave_height_m=round(float(wave), 2),
                wave_direction_deg=round(float(_pick(mh.get("wave_direction"), hour) or 0.0), 1),
                current_speed_kn=round(float(_pick(mh.get("ocean_current_velocity"), hour) or 0.0) * 0.5399568, 2),
                current_direction_deg=round(float(_pick(mh.get("ocean_current_direction"), hour) or 0.0), 1),
                # Open-Meteo reports visibility in metres and only for some models.
                visibility_nm=round(float(vis_m) / 1852.0, 1) if vis_m is not None else 8.0,
                temperature_c=round(float(_pick(ah.get("temperature_2m"), hour) or 0.0), 1),
                source=self.name,
            )
        return out


def _as_list(payload) -> list[dict]:
    return payload if isinstance(payload, list) else [payload]


def _pick(series, hour: int):
    if not series or hour >= len(series):
        return None
    return series[hour]


# ---------------------------------------------------------------------------
# Factory + route sampling
# ---------------------------------------------------------------------------

_provider: WeatherProvider | None = None


def get_provider() -> WeatherProvider:
    global _provider
    if _provider is None:
        mock = MockWeatherProvider()
        mode = settings.weather_provider
        if mode in ("open-meteo", "openmeteo", "auto"):
            _provider = OpenMeteoWeatherProvider(fallback=mock)
        else:
            _provider = mock
    return _provider


def reset_provider() -> None:
    """Used by tests."""
    global _provider
    _provider = None


def sample_along_route(
    points: list[Point],
    departure: datetime,
    duration_hours: float,
    max_samples: int = 10,
) -> list[WeatherSample]:
    """Sample weather at evenly spaced points along a route, advancing time."""
    if not points:
        return []
    count = max(2, min(max_samples, len(points)))
    step = (len(points) - 1) / (count - 1)
    picked = [points[int(round(i * step))] for i in range(count)]
    provider = get_provider()
    samples: list[WeatherSample] = []
    for i, p in enumerate(picked):
        at = departure + timedelta(hours=duration_hours * (i / max(1, count - 1)))
        samples.append(provider.get_many([p], at.replace(microsecond=0))[0])
    return samples


def aggregate(samples: list[WeatherSample]) -> dict:
    if not samples:
        return {
            "mean_wind_kn": 0.0,
            "max_wave_m": 0.0,
            "mean_wave_m": 0.0,
            "risk_index": 0.0,
            "risk_band": "VERY_LOW",
            "source": "NONE",
        }
    risks = [risk_index_for(s) for s in samples]
    # Worst conditions matter more than the average for routing decisions.
    index = 0.6 * (sum(risks) / len(risks)) + 0.4 * max(risks)
    sources = {s.source for s in samples}
    return {
        "mean_wind_kn": round(sum(s.wind_speed_kn for s in samples) / len(samples), 1),
        "max_wave_m": round(max(s.wave_height_m for s in samples), 2),
        "mean_wave_m": round(sum(s.wave_height_m for s in samples) / len(samples), 2),
        "risk_index": round(index, 4),
        "risk_band": risk_band(index),
        "source": "MIXED" if len(sources) > 1 else sources.pop(),
    }


def heading_exposure(heading: float, sample: WeatherSample) -> float:
    """1.0 when the sea is dead ahead, 0.0 when it is astern.

    Wave direction follows the meteorological convention: the direction the
    waves come from.
    """
    angle = relative_angle(heading, sample.wave_direction_deg)
    return round(math.cos(math.radians(angle)) * 0.5 + 0.5, 4)
