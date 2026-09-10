"""Open-Meteo provider tests.

The live API is not called here. A stub HTTP client returns payloads in the
shape Open-Meteo documents, so the parsing, unit conversion, hour matching,
batching and fallback behaviour are all checked without a network.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.services import weather as weather_service
from app.services.weather import (
    MockWeatherProvider,
    OpenMeteoWeatherProvider,
    aggregate,
)


def _hourly_times(start: datetime, hours: int) -> list[str]:
    return [(start + timedelta(hours=i)).strftime("%Y-%m-%dT%H:00") for i in range(hours)]


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeClient:
    """Stands in for httpx.Client. Records every call it is given."""

    calls: list[tuple] = []
    fail = False
    marine_nulls_for: set[int] = set()

    def __init__(self, *_args, **_kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def get(self, url, params=None):
        FakeClient.calls.append((url, params))
        if FakeClient.fail:
            raise RuntimeError("network down")

        count = len(params["latitude"].split(","))
        start = datetime.fromisoformat(params["start_date"])
        end = datetime.fromisoformat(params["end_date"])
        hours = int((end - start).total_seconds() // 3600) + 24
        times = _hourly_times(start, hours)

        payloads = []
        for n in range(count):
            if "marine" in url:
                nulls = n in FakeClient.marine_nulls_for
                payloads.append(
                    {
                        "hourly": {
                            "time": times,
                            # 3.20 m at every step keeps the assertions simple.
                            "wave_height": [None if nulls else 3.2] * hours,
                            "wave_direction": [None if nulls else 245.0] * hours,
                            "wave_period": [None if nulls else 8.4] * hours,
                            "swell_wave_height": [None if nulls else 2.1] * hours,
                            # km/h in the API; 3.7 km/h is almost exactly 2 kn.
                            "ocean_current_velocity": [None if nulls else 3.7] * hours,
                            "ocean_current_direction": [None if nulls else 95.0] * hours,
                        }
                    }
                )
            else:
                payloads.append(
                    {
                        "hourly": {
                            "time": times,
                            # Hour-varying so the time matching is testable.
                            "wind_speed_10m": [10.0 + i for i in range(hours)],
                            "wind_direction_10m": [230.0] * hours,
                            "visibility": [18520.0] * hours,  # metres -> 10.0 NM
                            "temperature_2m": [14.5] * hours,
                        }
                    }
                )
        return FakeResponse(payloads if count > 1 else payloads[0])


@pytest.fixture(autouse=True)
def stub_http(monkeypatch):
    FakeClient.calls = []
    FakeClient.fail = False
    FakeClient.marine_nulls_for = set()
    monkeypatch.setattr(httpx, "Client", FakeClient)
    yield
    weather_service.reset_provider()


@pytest.fixture
def provider():
    return OpenMeteoWeatherProvider(fallback=MockWeatherProvider(), timeout=1.0)


def _soon(hours: float = 3.0) -> datetime:
    return (datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0) + timedelta(hours=hours)).replace(
        minute=0, second=0
    )


def test_parses_a_documented_payload(provider):
    at = _soon()
    sample = provider.get_many([(35.0, -20.0)], at)[0]

    assert sample.source == "OPEN_METEO"
    assert sample.wave_height_m == 3.2
    assert sample.wave_direction_deg == 245.0
    assert sample.wave_period_s == 8.4
    assert sample.swell_wave_height_m == 2.1
    assert sample.temperature_c == 14.5


def test_unit_conversions(provider):
    """Current arrives in km/h and visibility in metres; both are converted."""
    sample = provider.get_many([(35.0, -20.0)], _soon())[0]

    assert sample.current_speed_kn == pytest.approx(2.0, abs=0.01)  # 3.7 km/h
    assert sample.visibility_nm == pytest.approx(10.0, abs=0.05)  # 18520 m


def test_wind_is_requested_in_knots_from_a_sea_cell(provider):
    provider.get_many([(35.0, -20.0)], _soon())
    atmos = [params for url, params in FakeClient.calls if "marine" not in url][0]

    assert atmos["wind_speed_unit"] == "kn"
    assert atmos["cell_selection"] == "sea"
    assert atmos["timezone"] == "UTC"


def test_picks_the_hour_nearest_the_requested_time(provider):
    """Wind rises by 1 kn per hour in the stub, so the value identifies the hour."""
    base = _soon(2)
    first = provider.get_many([(10.0, 10.0)], base)[0]
    later = provider.get_many([(10.0, 10.0)], base + timedelta(hours=5))[0]

    assert later.wind_speed_kn == pytest.approx(first.wind_speed_kn + 5.0, abs=0.01)


def test_rounds_to_the_closest_hour_not_down(provider):
    base = _soon(2)
    on_the_hour = provider.get_many([(11.0, 11.0)], base)[0]
    forty_minutes_past = provider.get_many([(11.5, 11.5)], base + timedelta(minutes=50))[0]

    assert forty_minutes_past.wind_speed_kn == pytest.approx(on_the_hour.wind_speed_kn + 1.0, abs=0.01)


def test_a_whole_route_costs_one_request_pair(provider):
    """Ten waypoints at ten different times must not mean twenty round trips."""
    start = _soon(1)
    requests = [((10.0 + i, 20.0 + i), start + timedelta(hours=6 * i)) for i in range(10)]

    samples = provider.get_at_times(requests)

    assert len(samples) == 10
    assert all(s.source == "OPEN_METEO" for s in samples)
    assert len(FakeClient.calls) == 2
    assert provider.requests_made == 2


def test_second_call_is_served_from_cache(provider):
    at = _soon()
    provider.get_many([(35.0, -20.0)], at)
    provider.get_many([(35.0, -20.0)], at)

    assert len(FakeClient.calls) == 2  # the first fetch only


def test_a_cell_without_marine_data_falls_back_alone(provider):
    FakeClient.marine_nulls_for = {1}
    start = _soon(1)
    requests = [((10.0, 20.0), start), ((11.0, 21.0), start), ((12.0, 22.0), start)]

    samples = provider.get_at_times(requests)

    assert [s.source for s in samples] == ["OPEN_METEO", "MOCK", "OPEN_METEO"]
    assert provider.fallback_samples == 1


def test_times_beyond_the_forecast_horizon_are_not_requested(provider):
    far = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)

    sample = provider.get_many([(35.0, -20.0)], far)[0]

    assert sample.source == "MOCK"
    assert FakeClient.calls == []


def test_network_failure_degrades_quietly(provider):
    FakeClient.fail = True

    sample = provider.get_many([(35.0, -20.0)], _soon())[0]

    assert sample.source == "MOCK"
    assert sample.wave_height_m > 0


def test_aggregate_reports_how_much_was_live(provider):
    FakeClient.marine_nulls_for = {0}
    start = _soon(1)
    samples = provider.get_at_times(
        [((10.0, 20.0), start), ((11.0, 21.0), start), ((12.0, 22.0), start), ((13.0, 23.0), start)]
    )

    summary = aggregate(samples)

    assert summary["live_fraction"] == 0.75
    assert summary["source"] == "MIXED"


def test_mock_provider_supplies_sea_state_detail():
    sample = MockWeatherProvider().get_many([(45.0, -30.0)], _soon())[0]

    assert sample.source == "MOCK"
    assert sample.wave_period_s is not None and 2.5 <= sample.wave_period_s <= 18.0
    assert sample.swell_wave_height_m is not None
    assert sample.swell_wave_height_m < sample.wave_height_m
