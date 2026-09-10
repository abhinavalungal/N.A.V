export type VoyageStatus = "PLANNED" | "ACTIVE" | "COMPLETED";
export type Objective = "MIN_FUEL" | "FASTEST" | "MIN_EMISSIONS" | "BALANCED";
export type RiskBand = "VERY_LOW" | "LOW" | "MODERATE" | "HIGH" | "SEVERE";

export interface Meta {
  app: string;
  version: string;
  ai_provider: string;
  ai_model: string | null;
  weather_provider: string;
  database: string;
}

export interface Company {
  id: number;
  name: string;
  country: string;
  fleet_segment: string;
}

export interface Vessel {
  id: number;
  imo: string;
  name: string;
  vessel_type: string;
  company_id: number;
  deadweight_t: number;
  design_speed_kn: number;
  current_speed_kn: number;
  fuel_type: string;
  base_consumption_mt_per_day: number;
  latitude: number;
  longitude: number;
  heading_deg: number;
  status: string;
  year_built: number;
  data_source: string;
  company?: Company | null;
}

export interface VesselDetail extends Vessel {
  current_voyage: Voyage | null;
  recent_voyages: Voyage[];
  historical: HistoricalVoyage[];
}

export interface Voyage {
  id: number;
  reference: string;
  vessel_id: number;
  origin_port: string;
  origin_lat: number;
  origin_lon: number;
  destination_port: string;
  destination_lat: number;
  destination_lon: number;
  departure_utc: string;
  expected_arrival_utc: string;
  required_arrival_utc: string | null;
  current_lat: number | null;
  current_lon: number | null;
  current_speed_kn: number;
  planned_speed_kn: number;
  distance_nm: number;
  distance_remaining_nm: number;
  planned_fuel_mt: number;
  consumed_fuel_mt: number;
  cargo_t: number;
  status: VoyageStatus;
  vessel_name?: string | null;
  vessel_imo?: string | null;
}

export interface Route {
  origin: number[];
  destination: number[];
  current: number[] | null;
  distance_nm: number;
  via: string[];
  geometry: number[][];
}

export interface RouteOption {
  code: string;
  label: string;
  distance_nm: number;
  speed_kn: number;
  via: string[];
  geometry: number[][];
}

export interface Weather {
  latitude: number;
  longitude: number;
  valid_at: string;
  wind_speed_kn: number;
  wind_direction_deg: number;
  wave_height_m: number;
  wave_direction_deg: number;
  current_speed_kn: number;
  current_direction_deg: number;
  visibility_nm: number;
  temperature_c: number;
  source: string;
  is_live: boolean;
}

export interface RouteWeather {
  samples: Weather[];
  mean_wind_kn: number;
  mean_wave_m: number;
  max_wave_m: number;
  risk_index: number;
  risk_band: RiskBand;
  source: string;
}

export interface OptimizationOption {
  id: number;
  code: string;
  label: string;
  distance_nm: number;
  average_speed_kn: number;
  duration_hours: number;
  eta_utc: string;
  fuel_mt: number;
  co2_mt: number;
  weather_risk: RiskBand;
  risk_index: number;
  score: number | null;
  feasible: boolean;
  infeasible_reason: string | null;
  breakdown_json: Record<string, any>;
  geometry_json: number[][];
  recommended: boolean;
}

export interface Recommendation {
  id: number;
  run_id: number;
  voyage_id: number;
  option_id: number;
  headline: string;
  rationale: string;
  fuel_saving_mt: number;
  co2_saving_mt: number;
  eta_delta_hours: number;
  status: "PENDING" | "APPROVED" | "REJECTED" | "MODIFIED";
  explanation_source: string;
  created_at: string;
  option?: OptimizationOption | null;
  vessel_name?: string | null;
  voyage_reference?: string | null;
  route_label?: string | null;
}

export interface ActivityStep {
  label: string;
  status: string;
}

export interface OptimizationRun {
  id: number;
  voyage_id: number;
  objective: Objective;
  status: string;
  message: string | null;
  weather_source: string;
  constraints_json: Record<string, any>;
  created_at: string;
  options: OptimizationOption[];
  recommendation: Recommendation | null;
  recommended_option_id: number | null;
  activity: ActivityStep[];
}

export interface VoyageDetail extends Voyage {
  vessel: Vessel;
  route: Route | null;
  weather_now: Weather | null;
  latest_run: OptimizationRun | null;
  pending_recommendation: Recommendation | null;
  progress_pct: number;
}

export interface HistoricalVoyage {
  id: number;
  vessel_id: number;
  reference: string;
  origin_port: string;
  destination_port: string;
  departure_utc: string;
  arrival_utc: string;
  distance_nm: number;
  average_speed_kn: number;
  predicted_fuel_mt: number;
  actual_fuel_mt: number;
  predicted_duration_hours: number;
  actual_duration_hours: number;
  co2_mt: number;
  fuel_type: string;
  data_source: string;
}

export interface HistoryComparison {
  vessel_id: number;
  vessel_name: string;
  sample_size: number;
  average_speed_kn: number;
  average_fuel_mt: number;
  average_fuel_per_nm_kg: number;
  average_duration_hours: number;
  average_fuel_variance_pct: number;
  average_eta_variance_hours: number;
  voyages: HistoricalVoyage[];
  current_voyage: Voyage | null;
}

export interface FleetAnalytics {
  active_vessels: number;
  active_voyages: number;
  planned_voyages: number;
  completed_voyages: number;
  attention_required: number;
  optimization_opportunities: number;
  pending_approvals: number;
  potential_fuel_saving_mt: number;
  potential_co2_saving_mt: number;
  approved_fuel_saving_mt: number;
  fleet_fuel_mt: number;
  fleet_co2_mt: number;
  weather_source: string;
  fuel_by_vessel: Array<{
    vessel: string;
    voyage: string;
    planned_fuel_mt: number;
    consumed_fuel_mt: number;
    co2_mt: number;
  }>;
  monthly_performance: Array<{
    month: string;
    predicted_fuel_mt: number;
    actual_fuel_mt: number;
    co2_mt: number;
    voyages: number;
  }>;
}

export interface VoyageAlert {
  voyage_id: number;
  reference: string;
  vessel_name: string;
  severity: "INFO" | "WATCH" | "ACTION";
  message: string;
}

export interface AgentStep {
  tool: string;
  label: string;
  status: string;
  detail: string | null;
}

export interface ChatResponse {
  session_id: string;
  answer: string;
  provider: string;
  steps: AgentStep[];
  data: Record<string, any>;
  duration_ms: number;
  run_id: number | null;
}

export interface AgentRun {
  id: number;
  session_id: string;
  voyage_id: number | null;
  question: string;
  answer: string;
  provider: string;
  steps_json: AgentStep[];
  duration_ms: number;
  status: string;
  created_at: string;
}

export interface Port {
  name: string;
  unlocode: string;
  country: string;
  coord: number[];
}

export interface FuelPrice {
  port: string;
  fuel_type: string;
  price_usd_per_mt: number;
  quoted_at: string;
  source: string;
}
