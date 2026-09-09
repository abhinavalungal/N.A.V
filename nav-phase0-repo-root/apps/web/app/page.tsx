import { RefreshButton } from "@/components/refresh-button";
import { PhaseProgress } from "@/components/phase-progress";
import { ServicePanel } from "@/components/service-panel";
import { StatusPanel } from "@/components/status-panel";
import { api } from "@/lib/api";

// Probes run per request; a cached status page would be a lie.
export const dynamic = "force-dynamic";

export default async function SystemStatusPage() {
  const [readiness, meta] = await Promise.all([api.readiness(), api.meta()]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">System status</h1>
          <p className="mt-1 max-w-prose text-sm text-muted">
            Phase 0 delivers the foundation only: the API, worker, database and cache
            wiring that every later phase sits on. No vessel, voyage or optimisation
            data exists yet.
          </p>
        </div>
        <RefreshButton />
      </div>

      <StatusPanel readiness={readiness} apiUrl={api.baseUrl} />

      <div className="grid gap-6 xl:grid-cols-2">
        <ServicePanel meta={meta} />
        <PhaseProgress />
      </div>
    </div>
  );
}
