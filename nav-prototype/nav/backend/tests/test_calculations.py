"""Tests for the deterministic maths: fuel, ETA, emissions, routing, weather."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.config import AUXILIARY_FUEL_MT_PER_DAY, EMISSION_FACTORS
from app.services.emissions import UnknownFuelType, calculate_emissions
from app.services.eta import calculate_eta
from app.services.fuel import calculate_fuel, speed_factor, weather_factor
from app.services.geo import haversine_nm
from app.services.routing import sea_route
from app.services.weather import MockWeatherProvider, aggregate, risk_band

DEPARTURE = datetime(2026, 9, 15, 6, 0, 0)


# --- fuel ------------------------------------------------------------------


def test_speed_factor_follows_the_cube_law():
    assert speed_factor(14.0, 14.0) == 1.0
    assert speed_factor(7.0, 14.0) == pytest.approx(0.125, rel=1e-6)
    assert speed_factor(12.0, 14.0) == pytest.approx((12 / 14) ** 3, rel=1e-6)


def test_fuel_is_daily_rate_times_days_times_factors():
    result = calculate_fuel(
        base_daily_mt=30.0,
        design_speed_kn=14.0,
        speed_kn=14.0,
        duration_hours=48.0,
        weather_multiplier=1.0,
    )
    assert result.propulsion_mt == pytest.approx(60.0)
    assert result.auxiliary_mt == pytest.approx(AUXILIARY_FUEL_MT_PER_DAY * 2)
    assert result.total_mt == pytest.approx(60.0 + AUXILIARY_FUEL_MT_PER_DAY * 2)


def test_slower_steaming_burns_less_fuel_per_voyage():
    fast = calculate_fuel(30.0, 14.0, 14.0, 1000 / 14.0)
    slow = calculate_fuel(30.0, 14.0, 11.2, 1000 / 11.2)
    assert slow.total_mt < fast.total_mt


def test_fuel_is_deterministic():
    a = calculate_fuel(26.0, 14.5, 13.0, 200.0, 1.07)
    b = calculate_fuel(26.0, 14.5, 13.0, 200.0, 1.07)
    assert a.to_dict() == b.to_dict()


def test_weather_factor_rises_with_sea_state_and_is_capped():
    calm = weather_factor(0.5, 8.0)
    rough = weather_factor(5.0, 35.0)
    storm = weather_factor(15.0, 80.0)
    assert calm < rough < 1.6
    assert storm == 1.6  # MAX_WEATHER_FACTOR
    assert weather_factor(4.0, 25.0, head_sea_exposure=1.0) > weather_factor(
        4.0, 25.0, head_sea_exposure=0.0
    )


def test_fuel_rejects_invalid_input():
    with pytest.raises(ValueError):
        calculate_fuel(30.0, 14.0, 0.0, 24.0)
    with pytest.raises(ValueError):
        calculate_fuel(0.0, 14.0, 12.0, 24.0)


# --- ETA -------------------------------------------------------------------


def test_eta_is_distance_over_speed_plus_allowance():
    eta = calculate_eta(3420.0, 13.5, DEPARTURE, port_allowance_hours=0.0)
    assert eta.sea_hours == pytest.approx(3420 / 13.5, abs=0.01)
    assert eta.eta_utc == DEPARTURE + timedelta(hours=3420 / 13.5)


def test_favourable_current_brings_the_eta_forward():
    against = calculate_eta(1000.0, 12.0, DEPARTURE, current_assist_kn=-1.0)
    neutral = calculate_eta(1000.0, 12.0, DEPARTURE)
    withit = calculate_eta(1000.0, 12.0, DEPARTURE, current_assist_kn=1.0)
    assert withit.eta_utc < neutral.eta_utc < against.eta_utc


def test_eta_rejects_zero_speed():
    with pytest.raises(ValueError):
        calculate_eta(1000.0, 0.0, DEPARTURE)


# --- emissions -------------------------------------------------------------


def test_co2_uses_the_configured_emission_factor():
    result = calculate_emissions(100.0, "VLSFO")
    assert result.emission_factor == EMISSION_FACTORS["VLSFO"]
    assert result.co2_mt == pytest.approx(100.0 * EMISSION_FACTORS["VLSFO"], rel=1e-9)


def test_fuel_types_are_supported_and_validated():
    for fuel_type in ("VLSFO", "HSFO", "MGO"):
        assert calculate_emissions(10.0, fuel_type).co2_mt > 0
    with pytest.raises(UnknownFuelType):
        calculate_emissions(10.0, "PIXIE_DUST")


def test_intensity_metrics_need_distance_and_deadweight():
    plain = calculate_emissions(100.0, "MGO")
    full = calculate_emissions(100.0, "MGO", distance_nm=2000.0, deadweight_t=50_000.0)
    assert plain.aer_g_per_dwt_nm is None
    assert full.co2_per_nm_kg == pytest.approx(full.co2_mt * 1000 / 2000, rel=1e-6)
    assert full.aer_g_per_dwt_nm == pytest.approx(
        full.co2_mt * 1_000_000 / (50_000 * 2000), rel=1e-6
    )


# --- routing ---------------------------------------------------------------


def test_haversine_matches_a_known_distance():
    # Rotterdam pilot station to the Dover strait, about 114 NM.
    assert haversine_nm((51.949, 4.140), (50.9, 1.6)) == pytest.approx(114, abs=5)
    # One degree of latitude is 60 NM by definition.
    assert haversine_nm((0.0, 0.0), (1.0, 0.0)) == pytest.approx(60, abs=0.5)


def test_suez_route_is_shorter_than_the_cape_and_follows_sea_lanes():
    _points, via, distance = sea_route("Singapore", "Rotterdam")
    assert 7500 < distance < 9500  # published distance is about 8,300 NM
    assert "SUEZ_N" in via and "GIBRALTAR" in via


def test_route_is_symmetric():
    _p1, _v1, out = sea_route("Fujairah", "Singapore")
    _p2, _v2, back = sea_route("Singapore", "Fujairah")
    assert out == pytest.approx(back, rel=1e-6)


# --- weather ---------------------------------------------------------------


def test_mock_weather_is_deterministic_and_labelled():
    provider = MockWeatherProvider()
    a = provider.get((10.0, 65.0), DEPARTURE)
    b = provider.get((10.0, 65.0), DEPARTURE)
    assert a.to_dict() == b.to_dict()
    assert a.source == "MOCK"


def test_mock_weather_stays_in_physical_ranges():
    provider = MockWeatherProvider()
    for lat in range(-60, 61, 15):
        for lon in range(-180, 181, 45):
            s = provider.get((float(lat), float(lon)), DEPARTURE)
            assert 0 < s.wind_speed_kn <= 60
            assert 0 < s.wave_height_m <= 9
            assert 0 <= s.wind_direction_deg < 360
            assert 0 < s.visibility_nm <= 12


def test_risk_bands_are_ordered():
    assert risk_band(0.05) == "VERY_LOW"
    assert risk_band(0.45) == "MODERATE"
    assert risk_band(0.95) == "SEVERE"


def test_aggregate_reports_the_source():
    provider = MockWeatherProvider()
    samples = provider.get_many([(10.0, 65.0), (12.0, 60.0)], DEPARTURE)
    result = aggregate(samples)
    assert result["source"] == "MOCK"
    assert result["max_wave_m"] >= result["mean_wave_m"]
