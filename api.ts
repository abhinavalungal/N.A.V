import type {
  AgentRun,
  ChatResponse,
  FleetAnalytics,
  FuelPrice,
  HistoryComparison,
  Meta,
  OptimizationRun,
  Port,
  Recommendation,
  RouteOption,
  RouteWeather,
  Vessel,
  VesselDetail,
  Voyage,
  VoyageAlert,
  VoyageDetail,
  VoyagePlan,
  Weather,
  WindField,
} from "@/types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      "Can't reach the N.A.V. backend. Start it with: uvicorn app.main:app --reload",
      0,
    );
  }
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      detail = body.detail || body.error || detail;
    } catch {
      /* keep the status line */
    }
    throw new ApiError(detail, response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

const post = <T,>(path: string, body: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) });

export const api = {
  meta: () => request<Meta>("/meta"),

  vessels: (search?: string) =>
    request<Vessel[]>(`/vessels${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  vessel: (id: number) => request<VesselDetail>(`/vessels/${id}`),
  vesselHistory: (id: number, limit = 10) =>
    request<HistoryComparison>(`/vessels/${id}/history?limit=${limit}`),

  voyages: (status?: string) =>
    request<Voyage[]>(`/voyages${status ? `?status=${status}` : ""}`),
  voyage: (id: number) => request<VoyageDetail>(`/voyages/${id}`),
  voyageRoutes: (id: number) => request<RouteOption[]>(`/voyages/${id}/routes`),
  voyagePlan: (id: number, opts: { speed?: number; legs?: number } = {}) => {
    const q = new URLSearchParams();
    if (opts.speed) q.set("speed_kn", String(opts.speed));
    q.set("legs", String(opts.legs ?? 10));
    return request<VoyagePlan>(`/voyages/${id}/plan?${q.toString()}`);
  },
  windField: (voyageId: number, at?: string) =>
    request<WindField>(
      `/weather/voyage/${voyageId}/field${at ? `?at=${encodeURIComponent(at)}` : ""}`,
    ),

  voyageHistory: (id: number, limit = 5) =>
    request<HistoryComparison>(`/voyages/${id}/history?limit=${limit}`),
  createVoyage: (body: Record<string, unknown>) => post<Voyage>("/voyages", body),
  ports: () => request<Port[]>("/ports"),

  weather: (vesselId: number) => request<Weather>(`/weather/${vesselId}`),
  trackWeather: (voyageId: number) =>
    request<RouteWeather>(`/weather/voyage/${voyageId}/track`),

  optimize: (body: {
    voyage_id: number;
    objective: string;
    constraints: Record<string, unknown>;
  }) => post<OptimizationRun>("/optimization", body),
  optimizationRun: (id: number) => request<OptimizationRun>(`/optimization/${id}`),
  optimizationRuns: (voyageId?: number) =>
    request<OptimizationRun[]>(`/optimization${voyageId ? `?voyage_id=${voyageId}` : ""}`),

  recommendations: (status?: string) =>
    request<Recommendation[]>(`/recommendations${status ? `?status=${status}` : ""}`),
  approve: (id: number, comment?: string) =>
    post<Recommendation>(`/recommendations/${id}/approve`, { comment }),
  reject: (id: number, comment?: string) =>
    post<Recommendation>(`/recommendations/${id}/reject`, { comment }),
  modify: (id: number, optionId: number, comment?: string) =>
    post<Recommendation>(`/recommendations/${id}/modify`, { option_id: optionId, comment }),

  chat: (body: { message: string; session_id?: string; voyage_id?: number | null }) =>
    post<ChatResponse>("/agent/chat", body),
  agentRuns: (limit = 20) => request<AgentRun[]>(`/agent/runs?limit=${limit}`),

  fleet: () => request<FleetAnalytics>("/analytics/fleet"),
  alerts: () => request<VoyageAlert[]>("/analytics/alerts"),
  fuelPrices: () => request<FuelPrice[]>("/fuel/prices"),
};
