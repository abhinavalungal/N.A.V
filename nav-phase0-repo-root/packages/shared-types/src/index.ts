/**
 * Types shared across the N.A.V. monorepo.
 *
 * These mirror the Pydantic schemas in apps/api/app/schemas. Keeping one
 * definition means a contract change breaks the build rather than the console.
 */

/**
 * Status of a single dependency. Never inferred - only ever reported.
 * NOT_CONFIGURED is a deliberate omission, not a fault, and does not block
 * readiness.
 */
export type ComponentStatus = "UP" | "DOWN" | "NOT_CONFIGURED" | "UNKNOWN";

export interface ComponentHealth {
  name: string;
  status: ComponentStatus;
  /** Round-trip time of the probe; null when the probe never ran. */
  latency_ms: number | null;
  /** Short reason when the component is not UP. */
  detail: string | null;
}

export interface LivenessResponse {
  status: string;
  service: string;
  version: string;
  environment: string;
  timestamp: string;
}

export interface ReadinessResponse {
  ready: boolean;
  service: string;
  version: string;
  environment: string;
  timestamp: string;
  components: ComponentHealth[];
}

export interface MetaResponse {
  name: string;
  full_name: string;
  version: string;
  environment: string;
  phase: string;
  api_version: string;
  /** Providers currently returning mock data. The console labels these. */
  mock_providers: string[];
  llm_provider: string;
  weather_provider: string;
  routing_provider: string;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
    request_id: string | null;
  };
}

/**
 * Result of a call that is allowed to fail. The console renders the failure
 * instead of substituting a plausible value.
 */
export type Fetched<T> =
  | { ok: true; data: T }
  | { ok: false; reason: string };
