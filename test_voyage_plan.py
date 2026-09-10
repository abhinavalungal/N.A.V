"""Voyage plan tests: legs, hazards and the wind grid."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import pytest

from app.services import weather as weather_service
from app.services.voyage_plan import (
    GALE_WIND_KN,
    Leg,
    hazard_segments,
    leg_schedule,
    wind_field,
)


@dataclass
class FakeVessel:
    design_speed_kn: float = 14.0
    base_consumption_mt_per_day: float = 28.0


# North Atlantic-ish track, west to east.
TRACK = [(40.0, -60.0), (44.0, -45.0), (48.0, -30.0), (50.0, -15.0), (51.0, -5.0)]
DEPARTURE = datetime(2026, 5, 1, 6, 0)


@pytest.fixture(autouse=True)
def deterministic_weather(monkeypatch):
    monkeypatch.setattr(weather_service.settings, "weather_provider", "mock")
    weather_service.reset_provider()
    yield
    weather_service.reset_provider()


def test_legs_cover_the_track_and_advance_in_time():
    legs = leg_schedule(TRACK, 12.0, DEPARTURE, FakeVessel(), max_legs=4)

    assert len(legs) == 4
    assert legs[0].depart_utc == DEPARTURE
    assert legs[0].start == TRACK[0]
    assert legs[-1].end == TRACK[-1]
    for earlier, later in zip(legs, legs[1:]):
        assert later.depart_utc == earlier.arrive_utc


def test_leg_duration_matches_distance_over_speed():
    legs = leg_schedule(TRACK, 12.0, DEPARTURE, FakeVessel(), max_legs=4)

    for leg in legs:
        hours = (leg.arrive_utc - leg.depart_utc).total_seconds() / 3600
        assert hours == pytest.approx(leg.distance_nm / 12.0, rel=1e-6)


def test_slower_steaming_burns_less_over_the_same_track():
    fast = leg_schedule(TRACK, 14.0, DEPARTURE, FakeVessel(), max_legs=4)
    slow = leg_schedule(TRACK, 11.0, DEPARTURE, FakeVessel(), max_legs=4)

    assert sum(l.fuel_mt for l in slow) < sum(l.fuel_mt for l in fast)


def test_every_leg_carries_the_weather_it_was_costed_with():
    legs = leg_schedule(TRACK, 12.0, DEPARTURE, FakeVessel(), max_legs=5)

    for leg in legs:
        assert leg.weather_source == "MOCK"
        assert leg.wind_speed_kn > 0
        assert 0.0 <= leg.exposure <= 1.0
        assert 0.0 <= leg.risk_index <= 1.0


def _leg(index: int, wind: float, wave: float, hour: int) -> Leg:
    start = DEPARTURE + timedelta(hours=hour)
    return Leg(
        index=index,
        start=(40.0, -50.0),
        end=(41.0, -48.0),
        depart_utc=start,
        arrive_utc=start + timedelta(hours=6),
        distance_nm=100.0,
        speed_kn=12.0,
        heading_deg=90.0,
        fuel_mt=10.0,
        wind_speed_kn=wind,
        wind_direction_deg=270.0,
        wave_height_m=wave,
        wave_direction_deg=270.0,
        current_speed_kn=0.5,
        weather_source="OPEN_METEO",
        exposure=0.5,
        risk_index=0.4,
    )


def test_calm_legs_produce_no_hazard():
    legs = [_leg(i, 18.0, 1.8, i * 6) for i in range(4)]

    assert hazard_segments(legs) == []


def test_consecutive_rough_legs_merge_into_one_window():
    legs = [
        _leg(1, 20.0, 2.0, 0),
        _leg(2, 38.0, 4.5, 6),
        _leg(3, 41.0, 5.2, 12),
        _leg(4, 19.0, 1.9, 18),
    ]

    hazards = hazard_segments(legs)

    assert len(hazards) == 1
    hazard = hazards[0]
    assert hazard.severity == "WATCH"
    assert hazard.max_wind_kn == 41.0
    assert hazard.max_wave_m == 5.2
    assert hazard.start_utc == legs[1].depart_utc
    assert hazard.end_utc == legs[2].arrive_utc
    assert "41 kn" in hazard.reason


def test_storm_force_is_flagged_dangerous_not_watch():
    legs = [_leg(1, 15.0, 1.5, 0), _leg(2, 52.0, 7.5, 6)]

    hazards = hazard_segments(legs)

    assert [h.severity for h in hazards] == ["DANGEROUS"]


def test_separate_rough_patches_stay_separate():
    legs = [
        _leg(1, 40.0, 4.2, 0),
        _leg(2, 15.0, 1.5, 6),
        _leg(3, 39.0, 4.4, 12),
    ]

    assert len(hazard_segments(legs)) == 2


def test_gale_threshold_is_the_trigger():
    below = [_leg(1, GALE_WIND_KN - 0.1, 1.0, 0)]
    at = [_leg(1, GALE_WIND_KN, 1.0, 0)]

    assert hazard_segments(below) == []
    assert len(hazard_segments(at)) == 1


def test_wind_field_covers_the_track_with_a_grid():
    grid = wind_field(TRACK, DEPARTURE, columns=5, rows=4)

    assert len(grid) == 20
    lats = [p.latitude for p in grid]
    lons = [p.longitude for p in grid]
    # The grid is padded out beyond the track on every side.
    assert min(lats) < min(p[0] for p in TRACK)
    assert max(lats) > max(p[0] for p in TRACK)
    assert min(lons) < min(p[1] for p in TRACK)
    assert all(-180 <= lon <= 180 for lon in lons)
    assert all(p.wind_speed_kn > 0 for p in grid)


def test_empty_track_yields_nothing():
    assert leg_schedule([], 12.0, DEPARTURE, FakeVessel()) == []
    assert wind_field([], DEPARTURE) == []
