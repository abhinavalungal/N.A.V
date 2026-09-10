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
KMH_TO_KN = 0.5399568
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
    # Sea state detail. Present for live data; the mock provider derives them.
    wave_period_s: float | None = None
    swell_wave_height_m: float | None = None

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

    def get_at_times(self, requests: list[tuple[Point, datetime]]) -> list[WeatherSample]:
        """Each point at its own time. Providers that can batch, override this."""
        return [self.get_many([point], at)[0] for point, at in requests]

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
            # Pierson-Moskowitz peak period for a fully developed sea.
            period = max(2.5, min(18.0, 0.79 * u_ms))
            swell_h = max(0.1, min(8.0, wave * 0.62))
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
                    wave_period_s=round(period, 1),
                    swell_wave_height_m=round(swell_h, 2),
                )
            )
        return out


class OpenMeteoWeatherProvider(WeatherProvider):
    """Live weather from Open-Meteo (free, no API key, no registration).

    Two endpoints are used per fetch, whatever the number of points:

    * ``api.open-meteo.com/v1/forecast`` for wind, visibility and temperature
    * ``marine-api.open-meteo.com/v1/marine`` for waves and surface current

    Both accept comma-separated coordinate lists and a date range, so a whole
    route is one request pair rather than one per waypoint. Each point then
    picks the hour nearest the time the vessel is expected to be there, read
    off the returned ``hourly.time`` array rather than assumed by index.

    Any failure - network down, rate limited, a time outside the forecast
    horizon, a grid cell with no marine data - degrades to the mock provider
    for the affected points only, and those samples say ``MOCK``.
    """

    name = "OPEN_METEO"

    # Open-Meteo keeps roughly three months of past forecast and, for marine,
    # about a week ahead. Requests outside that window are not attempted.
    PAST_LIMIT = timedelta(days=90)
    FUTURE_LIMIT = timedelta(days=7)

    ATMOS_VARS = "wind_speed_10m,wind_direction_10m,visibility,temperature_2m"
    MARINE_VARS = (
        "wave_height,wave_direction,wave_period,swell_wave_height,"
        "ocean_current_velocity,ocean_current_direction"
    )

    def __init__(self, fallback: WeatherProvider, timeout: float | None = None):
        self.fallback = fallback
        self.timeout = timeout or settings.weather_timeout_s
        self._cache: dict[tuple, WeatherSample] = {}
        # Counters the API surfaces so a deployment can see how much live data
        # it is actually getting.
        self.requests_made = 0
        self.live_samples = 0
        self.fallback_samples = 0

    @staticmethod
    def _key(point: Point, valid_at: datetime) -> tuple:
        return (round(point[0], 1), round(point[1], 1), valid_at.strftime("%Y-%m-%dT%H"))

    # -- public API ---------------------------------------------------------

    def get_many(self, points: list[Point], valid_at: datetime) -> list[WeatherSample]:
        return self.get_at_times([(p, valid_at) for p in points])

    def get_at_times(self, requests: list[tuple[Point, datetime]]) -> list[WeatherSample]:
        """One fetch for a whole route, each point at its own forecast hour."""
        if not requests:
            return []

        results: dict[int, WeatherSample] = {}
        pending: list[int] = []
        for i, (point, at) in enumerate(requests):
            cached = self._cache.get(self._key(point, at))
            if cached is not None:
                results[i] = cached
            else:
                pending.append(i)

        if pending:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            in_window = [
                i
                for i in pending
                if -self.PAST_LIMIT <= (requests[i][1] - now) <= self.FUTURE_LIMIT
            ]
            fetched: dict[int, WeatherSample] = {}
            if in_window:
                try:
                    fetched = self._fetch([(requests[i][0], requests[i][1]) for i in in_window], in_window)
                except Exception:  # noqa: BLE001 - any failure degrades to mock
                    fetched = {}
            for i, sample in fetched.items():
                self._cache[self._key(requests[i][0], requests[i][1])] = sample
                results[i] = sample
            self.live_samples += len(fetched)

            missing = [i for i in pending if i not in results]
            if missing:
                self.fallback_samples += len(missing)
                for i in missing:
                    point, at = requests[i]
                    results[i] = self.fallback.get_many([point], at)[0]

        return [results[i] for i in range(len(requests))]

    # -- fetching -----------------------------------------------------------

    def _fetch(self, wanted: list[tuple[Point, datetime]], idx: list[int]) -> dict:
        import httpx  # local import keeps the module importable without httpx

        lats = ",".join(f"{p[0]:.3f}" for p, _ in wanted)
        lons = ",".join(f"{p[1]:.3f}" for p, _ in wanted)
        times = [t for _, t in wanted]
        start = min(times).date()
        end = max(times).date()
        common = {
            "latitude": lats,
            "longitude": lons,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "timezone": "UTC",
        }

        with httpx.Client(timeout=self.timeout) as client:
            marine = client.get(MARINE_URL, params={**common, "hourly": self.MARINE_VARS})
            marine.raise_for_status()
            atmos = client.get(
                FORECAST_URL,
                params={
                    **common,
                    "hourly": self.ATMOS_VARS,
                    "wind_speed_unit": "kn",
                    # Waypoints are at sea; without this the API can snap a
                    # coastal point to a land grid cell.
                    "cell_selection": "sea",
                },
            )
            atmos.raise_for_status()
        self.requests_made += 2

        marine_series = _as_list(marine.json())
        atmos_series = _as_list(atmos.json())
        if len(marine_series) != len(wanted) or len(atmos_series) != len(wanted):
            raise ValueError("Open-Meteo returned an unexpected number of locations")

        out: dict[int, WeatherSample] = {}
        for n, ((point, at), m, a) in enumerate(zip(wanted, marine_series, atmos_series)):
            mh = m.get("hourly") or {}
            ah = a.get("hourly") or {}
            mi = _nearest_hour_index(mh.get("time"), at)
            ai = _nearest_hour_index(ah.get("time"), at)
            if mi is None or ai is None:
                continue

            wave = _pick(mh.get("wave_height"), mi)
            wind = _pick(ah.get("wind_speed_10m"), ai)
            if wave is None or wind is None:
                continue  # no marine data for this cell -> caller falls back

            vis_m = _pick(ah.get("visibility"), ai)
            # Open-Meteo reports ocean current velocity in km/h.
            current_kmh = _pick(mh.get("ocean_current_velocity"), mi)
            period = _pick(mh.get("wave_period"), mi)
            swell = _pick(mh.get("swell_wave_height"), mi)

            out[idx[n]] = WeatherSample(
                latitude=round(point[0], 4),
                longitude=round(point[1], 4),
                valid_at=at,
                wind_speed_kn=round(float(wind), 1),
                wind_direction_deg=round(float(_pick(ah.get("wind_direction_10m"), ai) or 0.0), 1),
                wave_height_m=round(float(wave), 2),
                wave_direction_deg=round(float(_pick(mh.get("wave_direction"), mi) or 0.0), 1),
                current_speed_kn=round(float(current_kmh or 0.0) * KMH_TO_KN, 2),
                current_direction_deg=round(
                    float(_pick(mh.get("ocean_current_direction"), mi) or 0.0), 1
                ),
                # Visibility comes back in metres, and only from some models.
                visibility_nm=round(float(vis_m) / 1852.0, 1) if vis_m is not None else 8.0,
                temperature_c=round(float(_pick(ah.get("temperature_2m"), ai) or 0.0), 1),
                source=self.name,
                wave_period_s=round(float(period), 1) if period is not None else None,
                swell_wave_height_m=round(float(swell), 2) if swell is not None else None,
            )
        return out


def _as_list(payload) -> list[dict]:
    return payload if isinstance(payload, list) else [payload]


def _pick(series, index: int):
    if not series or index >= len(series):
        return None
    return series[index]


def _nearest_hour_index(times, at: datetime) -> int | None:
    """Index of the hourly step closest to `at`, read off the API's own times.

    Open-Meteo returns "2026-09-10T13:00" strings in the requested timezone
    (UTC here). Matching against them beats assuming the array starts at
    midnight, which breaks the moment a range or a model offset shifts it.
    """
    if not times:
        return None
    best_i: int | None = None
    best_delta: float | None = None
    for i, stamp in enumerate(times):
        try:
            moment = datetime.fromisoformat(str(stamp))
        except ValueError:
            continue
        if moment.tzinfo is not None:
            moment = moment.astimezone(timezone.utc).replace(tzinfo=None)
        delta = abs((moment - at).total_seconds())
        if best_delta is None or delta < best_delta:
            best_delta, best_i = delta, i
    # More than 90 minutes away means the series does not cover this time.
    if best_delta is None or best_delta > 5400:
        return None
    return best_i


# ---------------------------------------------------------------------------
# Factory + route sampling
# ---------------------------------------------------------------------------

_provider: WeatherProvider | None = None


def get_provider() -> WeatherProvider:
    global _provider
    if _provider is None:
        mock = MockWeatherProvider()
        mode = settings.weather_provider
        if mode in ("open-meteo", "open_meteo", "openmeteo", "live", "auto"):
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
    requests = [
        (
            p,
            (departure + timedelta(hours=duration_hours * (i / max(1, count - 1)))).replace(
                microsecond=0
            ),
        )
        for i, p in enumerate(picked)
    ]
    # One provider call for the whole track: the live provider turns this into
    # a single request pair rather than one round trip per waypoint.
    return get_provider().get_at_times(requests)


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
    live = sum(1 for s in samples if s.source == "OPEN_METEO")
    return {
        "mean_wind_kn": round(sum(s.wind_speed_kn for s in samples) / len(samples), 1),
        "max_wave_m": round(max(s.wave_height_m for s in samples), 2),
        "mean_wave_m": round(sum(s.wave_height_m for s in samples) / len(samples), 2),
        "risk_index": round(index, 4),
        "risk_band": risk_band(index),
        "source": "MIXED" if len(sources) > 1 else sources.pop(),
        # How much of this track is real forecast rather than mock. Long
        # voyages run past the forecast horizon, so this is often partial.
        "live_fraction": round(live / len(samples), 3),
    }


def heading_exposure(heading: float, sample: WeatherSample) -> float:
    """1.0 when the sea is dead ahead, 0.0 when it is astern.

    Wave direction follows the meteorological convention: the direction the
    waves come from.
    """
    angle = relative_angle(heading, sample.wave_direction_deg)
    return round(math.cos(math.radians(angle)) * 0.5 + 0.5, 4)
