"""Optimizer, constraint handling, approvals and the mock agent."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.ai.provider import MockAIProvider
from app.clock import utc_now
from app.database import Base
from app.models import Company, Vessel, Voyage
from app.services import weather as weather_service
from app.services.agent import run_agent
from app.services.eta import calculate_eta
from app.services.fuel import calculate_fuel
from app.services.optimizer import Constraints, run_optimization
from app.services.routing import sea_route

weather_service._provider = weather_service.MockWeatherProvider()


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def voyage(db):
    company = Company(name="Test Shipping", country="Singapore", fleet_segment="Tankers")
    db.add(company)
    db.flush()
    vessel = Vessel(
        imo="9999999",
        name="Test Alpha",
        vessel_type="Product tanker",
        company_id=company.id,
        deadweight_t=50_000,
        design_speed_kn=14.5,
        current_speed_kn=13.0,
        fuel_type="VLSFO",
        base_consumption_mt_per_day=26.0,
        latitude=1.264,
        longitude=103.822,
        status="AT_SEA",
    )
    db.add(vessel)
    db.flush()

    _points, _via, distance = sea_route("Singapore", "Rotterdam")
    departure = utc_now().replace(microsecond=0)
    eta = calculate_eta(distance, 13.3, departure)
    fuel = calculate_fuel(26.0, 14.5, 13.3, eta.sea_hours)
    row = Voyage(
        reference="TA-2026-001",
        vessel_id=vessel.id,
        origin_port="Singapore",
        origin_lat=1.264,
        origin_lon=103.822,
        destination_port="Rotterdam",
        destination_lat=51.949,
        destination_lon=4.140,
        departure_utc=departure,
        expected_arrival_utc=eta.eta_utc,
        current_lat=1.264,
        current_lon=103.822,
        current_speed_kn=13.0,
        planned_speed_kn=13.3,
        distance_nm=distance,
        distance_remaining_nm=distance,
        planned_fuel_mt=fuel.total_mt,
        status="PLANNED",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_optimizer_produces_at_least_three_scored_options(db, voyage):
    run = run_optimization(db, voyage, "BALANCED", Constraints())
    assert run.status == "COMPLETED"
    assert len(run.options) >= 3
    assert all(o.fuel_mt > 0 and o.co2_mt > 0 for o in run.options)
    assert run.recommendation is not None
    assert run.recommended_option_id in {o.id for o in run.options}


def test_lower_score_wins_and_recommendation_matches(db, voyage):
    run = run_optimization(db, voyage, "MIN_FUEL", Constraints())
    scored = [o for o in run.options if o.score is not None]
    best = min(scored, key=lambda o: o.score)
    assert run.recommended_option_id == best.id
    # For a minimum fuel objective the winner must also be the least thirsty.
    assert best.fuel_mt == min(o.fuel_mt for o in scored)


def test_fastest_objective_picks_the_earliest_arrival(db, voyage):
    run = run_optimization(db, voyage, "FASTEST", Constraints())
    chosen = next(o for o in run.options if o.id == run.recommended_option_id)
    assert chosen.eta_utc == min(o.eta_utc for o in run.options if o.feasible)


def test_min_emissions_objective_picks_the_lowest_co2(db, voyage):
    run = run_optimization(db, voyage, "MIN_EMISSIONS", Constraints())
    chosen = next(o for o in run.options if o.id == run.recommended_option_id)
    assert chosen.co2_mt == min(o.co2_mt for o in run.options if o.feasible)


def test_max_speed_constraint_is_respected(db, voyage):
    run = run_optimization(db, voyage, "FASTEST", Constraints(max_speed_kn=12.0))
    for option in run.options:
        if option.feasible:
            assert option.average_speed_kn <= 12.0 + 1e-6


def test_impossible_constraints_return_no_feasible_option(db, voyage):
    run = run_optimization(
        db,
        voyage,
        "BALANCED",
        Constraints(required_arrival_utc=voyage.departure_utc + timedelta(hours=2)),
    )
    assert run.status == "NO_FEASIBLE_OPTION"
    assert run.recommendation is None
    assert "No feasible option found" in run.message
    assert all(not o.feasible for o in run.options)
    assert all(o.infeasible_reason for o in run.options)


def test_weather_risk_constraint_can_exclude_options(db, voyage):
    run = run_optimization(db, voyage, "BALANCED", Constraints(max_weather_risk="VERY_LOW"))
    excluded = [o for o in run.options if not o.feasible]
    for option in excluded:
        assert "weather risk" in (option.infeasible_reason or "")


def test_savings_are_measured_against_the_fastest_option(db, voyage):
    run = run_optimization(db, voyage, "MIN_FUEL", Constraints())
    fastest = next(o for o in run.options if o.code == "FASTEST")
    chosen = next(o for o in run.options if o.id == run.recommended_option_id)
    assert run.recommendation.fuel_saving_mt == pytest.approx(
        round(fastest.fuel_mt - chosen.fuel_mt, 2), abs=0.01
    )
    assert "Based on prototype/mock" in run.recommendation.rationale


def test_unknown_objective_is_rejected(db, voyage):
    with pytest.raises(ValueError):
        run_optimization(db, voyage, "TELEPORT", Constraints())


# --- agent -----------------------------------------------------------------


def test_mock_agent_optimizes_and_quotes_real_numbers(db, voyage):
    result = run_agent(
        db,
        "Optimize this voyage for minimum fuel",
        voyage_id=voyage.id,
        provider=MockAIProvider(),
    )
    assert result["provider"] == "mock"
    assert any(s["tool"] == "optimize_voyage" for s in result["steps"])
    assert "Recommended:" in result["answer"]
    assert "prototype/mock data" in result["answer"]


def test_mock_agent_explains_the_last_run(db, voyage):
    run_optimization(db, voyage, "BALANCED", Constraints())
    result = run_agent(
        db, "Why did you choose this route?", voyage_id=voyage.id, provider=MockAIProvider()
    )
    assert any(s["tool"] == "get_latest_optimization" for s in result["steps"])
    assert "scores best" in result["answer"]


def test_mock_agent_answers_a_speed_what_if(db, voyage):
    result = run_agent(
        db,
        "What happens if I increase speed to 14 knots?",
        voyage_id=voyage.id,
        provider=MockAIProvider(),
    )
    assert any(s["tool"] == "calculate_fuel" for s in result["steps"])
    assert "14.0 kn" in result["answer"]


def test_agent_without_data_does_not_invent_an_answer(db):
    result = run_agent(db, "How much fuel will we save?", provider=MockAIProvider())
    assert "don't have enough data" in result["answer"] or "not found" in result["answer"].lower()
