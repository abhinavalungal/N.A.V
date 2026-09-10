"""Database tables. Deliberately flat and readable."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .clock import utc_now
from .database import Base


utcnow = utc_now  # column default


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    country: Mapped[str] = mapped_column(String(60))
    fleet_segment: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    vessels: Mapped[list["Vessel"]] = relationship(back_populates="company")


class Vessel(Base):
    __tablename__ = "vessels"

    id: Mapped[int] = mapped_column(primary_key=True)
    imo: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    vessel_type: Mapped[str] = mapped_column(String(60))
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    deadweight_t: Mapped[float] = mapped_column(Float)
    design_speed_kn: Mapped[float] = mapped_column(Float)
    current_speed_kn: Mapped[float] = mapped_column(Float, default=0.0)
    fuel_type: Mapped[str] = mapped_column(String(20))
    base_consumption_mt_per_day: Mapped[float] = mapped_column(Float)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    heading_deg: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(30), default="AT_SEA")
    year_built: Mapped[int] = mapped_column(Integer, default=2015)
    data_source: Mapped[str] = mapped_column(String(20), default="DEMO")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    company: Mapped[Company] = relationship(back_populates="vessels")
    voyages: Mapped[list["Voyage"]] = relationship(
        back_populates="vessel", cascade="all, delete-orphan"
    )


class Voyage(Base):
    __tablename__ = "voyages"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    vessel_id: Mapped[int] = mapped_column(ForeignKey("vessels.id"))
    origin_port: Mapped[str] = mapped_column(String(80))
    origin_lat: Mapped[float] = mapped_column(Float)
    origin_lon: Mapped[float] = mapped_column(Float)
    destination_port: Mapped[str] = mapped_column(String(80))
    destination_lat: Mapped[float] = mapped_column(Float)
    destination_lon: Mapped[float] = mapped_column(Float)
    departure_utc: Mapped[datetime] = mapped_column(DateTime)
    expected_arrival_utc: Mapped[datetime] = mapped_column(DateTime)
    required_arrival_utc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    current_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_speed_kn: Mapped[float] = mapped_column(Float, default=0.0)
    planned_speed_kn: Mapped[float] = mapped_column(Float, default=12.0)
    distance_nm: Mapped[float] = mapped_column(Float)
    distance_remaining_nm: Mapped[float] = mapped_column(Float)
    planned_fuel_mt: Mapped[float] = mapped_column(Float)
    consumed_fuel_mt: Mapped[float] = mapped_column(Float, default=0.0)
    cargo_t: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="PLANNED", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    vessel: Mapped[Vessel] = relationship(back_populates="voyages")
    positions: Mapped[list["VesselPosition"]] = relationship(
        back_populates="voyage", cascade="all, delete-orphan"
    )
    runs: Mapped[list["OptimizationRun"]] = relationship(
        back_populates="voyage", cascade="all, delete-orphan"
    )


class VesselPosition(Base):
    __tablename__ = "vessel_positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    vessel_id: Mapped[int] = mapped_column(ForeignKey("vessels.id"), index=True)
    voyage_id: Mapped[int | None] = mapped_column(ForeignKey("voyages.id"), nullable=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    speed_kn: Mapped[float] = mapped_column(Float)
    heading_deg: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, index=True)

    voyage: Mapped[Voyage | None] = relationship(back_populates="positions")


class WeatherRecord(Base):
    __tablename__ = "weather"

    id: Mapped[int] = mapped_column(primary_key=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    valid_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    wind_speed_kn: Mapped[float] = mapped_column(Float)
    wind_direction_deg: Mapped[float] = mapped_column(Float)
    wave_height_m: Mapped[float] = mapped_column(Float)
    wave_direction_deg: Mapped[float] = mapped_column(Float)
    current_speed_kn: Mapped[float] = mapped_column(Float)
    current_direction_deg: Mapped[float] = mapped_column(Float)
    visibility_nm: Mapped[float] = mapped_column(Float)
    temperature_c: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(20), default="MOCK")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class FuelPrice(Base):
    __tablename__ = "fuel_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    port: Mapped[str] = mapped_column(String(80))
    fuel_type: Mapped[str] = mapped_column(String(20))
    price_usd_per_mt: Mapped[float] = mapped_column(Float)
    quoted_at: Mapped[datetime] = mapped_column(DateTime)
    source: Mapped[str] = mapped_column(String(20), default="DEMO")


class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    voyage_id: Mapped[int] = mapped_column(ForeignKey("voyages.id"), index=True)
    objective: Mapped[str] = mapped_column(String(30))
    constraints_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="COMPLETED")
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    weather_source: Mapped[str] = mapped_column(String(20), default="MOCK")
    baseline_option_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recommended_option_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    voyage: Mapped[Voyage] = relationship(back_populates="runs")
    options: Mapped[list["OptimizationOption"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    recommendation: Mapped["Recommendation | None"] = relationship(
        back_populates="run", cascade="all, delete-orphan", uselist=False
    )


class OptimizationOption(Base):
    __tablename__ = "optimization_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("optimization_runs.id"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    label: Mapped[str] = mapped_column(String(80))
    distance_nm: Mapped[float] = mapped_column(Float)
    average_speed_kn: Mapped[float] = mapped_column(Float)
    duration_hours: Mapped[float] = mapped_column(Float)
    eta_utc: Mapped[datetime] = mapped_column(DateTime)
    fuel_mt: Mapped[float] = mapped_column(Float)
    co2_mt: Mapped[float] = mapped_column(Float)
    weather_risk: Mapped[str] = mapped_column(String(20))
    risk_index: Mapped[float] = mapped_column(Float)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    feasible: Mapped[bool] = mapped_column(Boolean, default=True)
    infeasible_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    breakdown_json: Mapped[dict] = mapped_column(JSON, default=dict)
    geometry_json: Mapped[list] = mapped_column(JSON, default=list)

    run: Mapped[OptimizationRun] = relationship(back_populates="options")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("optimization_runs.id"), unique=True)
    voyage_id: Mapped[int] = mapped_column(ForeignKey("voyages.id"), index=True)
    option_id: Mapped[int] = mapped_column(ForeignKey("optimization_options.id"))
    headline: Mapped[str] = mapped_column(String(200))
    rationale: Mapped[str] = mapped_column(Text)
    fuel_saving_mt: Mapped[float] = mapped_column(Float, default=0.0)
    co2_saving_mt: Mapped[float] = mapped_column(Float, default=0.0)
    eta_delta_hours: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    explanation_source: Mapped[str] = mapped_column(String(20), default="DETERMINISTIC")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    run: Mapped[OptimizationRun] = relationship(back_populates="recommendation")
    approvals: Mapped[list["Approval"]] = relationship(
        back_populates="recommendation", cascade="all, delete-orphan"
    )


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(
        ForeignKey("recommendations.id"), index=True
    )
    decision: Mapped[str] = mapped_column(String(20))  # APPROVED / REJECTED / MODIFIED
    decided_by: Mapped[str] = mapped_column(String(80), default="Operations")
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    modified_option_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    recommendation: Mapped[Recommendation] = relationship(back_populates="approvals")


class HistoricalVoyage(Base):
    __tablename__ = "historical_voyages"

    id: Mapped[int] = mapped_column(primary_key=True)
    vessel_id: Mapped[int] = mapped_column(ForeignKey("vessels.id"), index=True)
    reference: Mapped[str] = mapped_column(String(40))
    origin_port: Mapped[str] = mapped_column(String(80))
    destination_port: Mapped[str] = mapped_column(String(80))
    departure_utc: Mapped[datetime] = mapped_column(DateTime)
    arrival_utc: Mapped[datetime] = mapped_column(DateTime)
    distance_nm: Mapped[float] = mapped_column(Float)
    average_speed_kn: Mapped[float] = mapped_column(Float)
    predicted_fuel_mt: Mapped[float] = mapped_column(Float)
    actual_fuel_mt: Mapped[float] = mapped_column(Float)
    predicted_duration_hours: Mapped[float] = mapped_column(Float)
    actual_duration_hours: Mapped[float] = mapped_column(Float)
    co2_mt: Mapped[float] = mapped_column(Float)
    fuel_type: Mapped[str] = mapped_column(String(20))
    data_source: Mapped[str] = mapped_column(String(20), default="DEMO")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(60), index=True)
    voyage_id: Mapped[int | None] = mapped_column(ForeignKey("voyages.id"), nullable=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(60), index=True)
    voyage_id: Mapped[int | None] = mapped_column(ForeignKey("voyages.id"), nullable=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(20))
    steps_json: Mapped[list] = mapped_column(JSON, default=list)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="COMPLETED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
