"""Pydantic models. Every endpoint returns one of these, never a loose dict."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ORM = ConfigDict(from_attributes=True)

VoyageStatus = Literal["PLANNED", "ACTIVE", "COMPLETED"]
Objective = Literal["MIN_FUEL", "FASTEST", "MIN_EMISSIONS", "BALANCED"]
RiskBand = Literal["VERY_LOW", "LOW", "MODERATE", "HIGH", "SEVERE"]


class Meta(BaseModel):
    app: str
    version: str
    ai_provider: str
    ai_model: str | None = None
    weather_provider: str
    database: str


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None


# --- Companies / vessels ---------------------------------------------------


class CompanyOut(BaseModel):
    model_config = ORM
    id: int
    name: str
    country: str
    fleet_segment: str


class VesselBase(BaseModel):
    imo: str = Field(min_length=5, max_length=20)
    name: str
    vessel_type: str
    deadweight_t: float = Field(gt=0)
    design_speed_kn: float = Field(gt=0, le=40)
    fuel_type: str
    base_consumption_mt_per_day: float = Field(gt=0)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class VesselCreate(VesselBase):
    company_id: int
    current_speed_kn: float = Field(default=0, ge=0, le=40)
    heading_deg: float = Field(default=0, ge=0, lt=360)
    status: str = "AT_SEA"
    year_built: int = 2015


class VesselOut(VesselBase):
    model_config = ORM
    id: int
    company_id: int
    current_speed_kn: float
    heading_deg: float
    status: str
    year_built: int
    data_source: str
    company: CompanyOut | None = None


class VesselDetail(VesselOut):
    current_voyage: "VoyageOut | None" = None
    recent_voyages: list["VoyageOut"] = []
    historical: list["HistoricalVoyageOut"] = []


# --- Voyages ---------------------------------------------------------------


class VoyageCreate(BaseModel):
    vessel_id: int
    origin_port: str
    destination_port: str
    departure_utc: datetime
    planned_speed_kn: float | None = Field(default=None, gt=0, le=40)
    required_arrival_utc: datetime | None = None
    cargo_t: float = 0.0
    reference: str | None = None
    origin_lat: float | None = None
    origin_lon: float | None = None
    destination_lat: float | None = None
    destination_lon: float | None = None


class VoyageOut(BaseModel):
    model_config = ORM
    id: int
    reference: str
    vessel_id: int
    origin_port: str
    origin_lat: float
    origin_lon: float
    destination_port: str
    destination_lat: float
    destination_lon: float
    departure_utc: datetime
    expected_arrival_utc: datetime
    required_arrival_utc: datetime | None
    current_lat: float | None
    current_lon: float | None
    current_speed_kn: float
    planned_speed_kn: float
    distance_nm: float
    distance_remaining_nm: float
    planned_fuel_mt: float
    consumed_fuel_mt: float
    cargo_t: float
    status: VoyageStatus
    vessel_name: str | None = None
    vessel_imo: str | None = None


class VoyageDetail(VoyageOut):
    vessel: VesselOut
    route: "RouteOut | None" = None
    weather_now: "WeatherOut | None" = None
    latest_run: "OptimizationRunOut | None" = None
    pending_recommendation: "RecommendationOut | None" = None
    progress_pct: float = 0.0


class PositionOut(BaseModel):
    model_config = ORM
    latitude: float
    longitude: float
    speed_kn: float
    heading_deg: float
    recorded_at: datetime


# --- Weather ---------------------------------------------------------------


class WeatherOut(BaseModel):
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
    source: str
    is_live: bool = False
    wave_period_s: float | None = None
    swell_wave_height_m: float | None = None


class RouteWeatherOut(BaseModel):
    samples: list[WeatherOut]
    mean_wind_kn: float
    mean_wave_m: float
    max_wave_m: float
    risk_index: float
    risk_band: RiskBand
    source: str
    # Share of the track covered by real forecast rather than mock data.
    live_fraction: float = 0.0


class LegOut(BaseModel):
    index: int
    start: list[float]
    end: list[float]
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
    exposure: float
    risk_index: float


class HazardOut(BaseModel):
    severity: str
    reason: str
    start_utc: datetime
    end_utc: datetime
    max_wind_kn: float
    max_wave_m: float
    geometry: list[list[float]]
    source: str


class VoyagePlanOut(BaseModel):
    voyage_id: int
    reference: str
    vessel_name: str
    departure_utc: datetime
    arrival_utc: datetime
    speed_kn: float
    distance_nm: float
    total_fuel_mt: float
    legs: list[LegOut]
    hazards: list[HazardOut]
    weather_source: str
    live_fraction: float


class WindFieldPointOut(BaseModel):
    latitude: float
    longitude: float
    wind_speed_kn: float
    wind_direction_deg: float
    wave_height_m: float
    source: str


class WindFieldOut(BaseModel):
    valid_at: datetime
    points: list[WindFieldPointOut]
    source: str
    live_fraction: float


# --- Routing ---------------------------------------------------------------


class RouteOut(BaseModel):
    origin: list[float]
    destination: list[float]
    current: list[float] | None = None
    distance_nm: float
    via: list[str]
    geometry: list[list[float]]


class RouteOptionOut(BaseModel):
    code: str
    label: str
    distance_nm: float
    speed_kn: float
    via: list[str]
    geometry: list[list[float]]


# --- Fuel / emissions ------------------------------------------------------


class FuelRequest(BaseModel):
    vessel_id: int
    distance_nm: float = Field(gt=0)
    speed_kn: float = Field(gt=0, le=40)
    wave_height_m: float = Field(default=1.5, ge=0)
    wind_speed_kn: float = Field(default=12.0, ge=0)


class FuelResponse(BaseModel):
    vessel_id: int
    distance_nm: float
    speed_kn: float
    duration_hours: float
    fuel_mt: float
    co2_mt: float
    daily_consumption_mt: float
    speed_factor: float
    weather_factor: float
    fuel_type: str
    emission_factor: float


class FuelPriceOut(BaseModel):
    model_config = ORM
    port: str
    fuel_type: str
    price_usd_per_mt: float
    quoted_at: datetime
    source: str


# --- Optimization ----------------------------------------------------------


class ConstraintsIn(BaseModel):
    max_speed_kn: float | None = Field(default=None, gt=0, le=40)
    min_speed_kn: float | None = Field(default=None, gt=0, le=40)
    required_arrival_utc: datetime | None = None
    max_weather_risk: RiskBand | None = None


class OptimizationRequest(BaseModel):
    voyage_id: int
    objective: Objective = "BALANCED"
    constraints: ConstraintsIn = ConstraintsIn()


class OptimizationOptionOut(BaseModel):
    model_config = ORM
    id: int
    code: str
    label: str
    distance_nm: float
    average_speed_kn: float
    duration_hours: float
    eta_utc: datetime
    fuel_mt: float
    co2_mt: float
    weather_risk: RiskBand
    risk_index: float
    score: float | None
    feasible: bool
    infeasible_reason: str | None
    breakdown_json: dict[str, Any]
    geometry_json: list[Any]
    recommended: bool = False


class RecommendationOut(BaseModel):
    model_config = ORM
    id: int
    run_id: int
    voyage_id: int
    option_id: int
    headline: str
    rationale: str
    fuel_saving_mt: float
    co2_saving_mt: float
    eta_delta_hours: float
    status: str
    explanation_source: str
    created_at: datetime
    option: OptimizationOptionOut | None = None
    vessel_name: str | None = None
    voyage_reference: str | None = None
    route_label: str | None = None


class OptimizationRunOut(BaseModel):
    model_config = ORM
    id: int
    voyage_id: int
    objective: Objective
    status: str
    message: str | None
    weather_source: str
    constraints_json: dict[str, Any]
    created_at: datetime
    options: list[OptimizationOptionOut]
    recommendation: RecommendationOut | None = None
    recommended_option_id: int | None = None
    activity: list[dict[str, Any]] = []


class ApprovalRequest(BaseModel):
    comment: str | None = None
    decided_by: str = "Operations"


class ModifyRequest(ApprovalRequest):
    option_id: int


class ApprovalOut(BaseModel):
    model_config = ORM
    id: int
    recommendation_id: int
    decision: str
    decided_by: str
    comment: str | None
    modified_option_id: int | None
    decided_at: datetime


# --- History / analytics ---------------------------------------------------


class HistoricalVoyageOut(BaseModel):
    model_config = ORM
    id: int
    vessel_id: int
    reference: str
    origin_port: str
    destination_port: str
    departure_utc: datetime
    arrival_utc: datetime
    distance_nm: float
    average_speed_kn: float
    predicted_fuel_mt: float
    actual_fuel_mt: float
    predicted_duration_hours: float
    actual_duration_hours: float
    co2_mt: float
    fuel_type: str
    data_source: str


class HistoryComparison(BaseModel):
    vessel_id: int
    vessel_name: str
    sample_size: int
    average_speed_kn: float
    average_fuel_mt: float
    average_fuel_per_nm_kg: float
    average_duration_hours: float
    average_fuel_variance_pct: float
    average_eta_variance_hours: float
    voyages: list[HistoricalVoyageOut]
    current_voyage: VoyageOut | None = None


class FleetAnalytics(BaseModel):
    active_vessels: int
    active_voyages: int
    planned_voyages: int
    completed_voyages: int
    attention_required: int
    optimization_opportunities: int
    pending_approvals: int
    potential_fuel_saving_mt: float
    potential_co2_saving_mt: float
    approved_fuel_saving_mt: float
    fleet_fuel_mt: float
    fleet_co2_mt: float
    weather_source: str
    fuel_by_vessel: list[dict[str, Any]]
    monthly_performance: list[dict[str, Any]]


class VoyageAlert(BaseModel):
    voyage_id: int
    reference: str
    vessel_name: str
    severity: Literal["INFO", "WATCH", "ACTION"]
    message: str


# --- Agent -----------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str = "default"
    voyage_id: int | None = None


class AgentStep(BaseModel):
    tool: str
    label: str
    status: str = "done"
    detail: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    provider: str
    steps: list[AgentStep]
    data: dict[str, Any] = {}
    duration_ms: int
    run_id: int | None = None


class AgentRunOut(BaseModel):
    model_config = ORM
    id: int
    session_id: str
    voyage_id: int | None
    question: str
    answer: str
    provider: str
    steps_json: list[Any]
    duration_ms: int
    status: str
    created_at: datetime


class ChatMessageOut(BaseModel):
    model_config = ORM
    id: int
    session_id: str
    voyage_id: int | None
    role: str
    content: str
    created_at: datetime


VesselDetail.model_rebuild()
VoyageDetail.model_rebuild()
