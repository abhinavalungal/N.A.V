/**
 * Server-side client for the N.A.V. API.
 *
 * Calls are allowed to fail. When one does, the caller receives a reason and
 * the console renders that reason - it never falls back to a cached or
 * invented value.
 */
import type {
  Fetched,
  LivenessResponse,
  MetaResponse,
  ReadinessResponse,
} from "@nav/shared-types";

const API_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
const TIMEOUT_MS = 4000;

async function getJson<T>(path: string): Promise<Fetched<T>> {
  try {
    const response = await fetch(`${API_URL}${path}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(TIMEOUT_MS),
      headers: { accept: "application/json" },
    });

    // 503 from /ready is a valid, meaningful body - not a transport failure.
    if (!response.ok && response.status !== 503) {
      return { ok: false, reason: `API responded ${response.status}` };
    }

    return { ok: true, data: (await response.json()) as T };
  } catch (error) {
    const reason =
      error instanceof DOMException && error.name === "TimeoutError"
        ? `No response within ${TIMEOUT_MS} ms`
        : "API unreachable";
    return { ok: false, reason };
  }
}

export const api = {
  liveness: () => getJson<LivenessResponse>("/health"),
  readiness: () => getJson<ReadinessResponse>("/ready"),
  meta: () => getJson<MetaResponse>("/api/v1/meta"),
  baseUrl: API_URL,
};
