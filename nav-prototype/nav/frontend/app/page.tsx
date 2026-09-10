"use client";

import { useRouter } from "next/navigation";
import { useMemo } from "react";

import { AssistantPanel } from "@/components/assistant/AssistantPanel";
import { RecommendationRail } from "@/components/dashboard/RecommendationRail";
import { StatStrip } from "@/components/dashboard/StatStrip";
import { VoyageTable } from "@/components/dashboard/VoyageTable";
import { Map } from "@/components/map/Map";
import { Panel, PanelHeader } from "@/components/ui/card";
import { ErrorNote, Loading } from "@/components/ui/feedback";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { num } from "@/lib/format";

export default function DashboardPage() {
  const router = useRouter();
  const fleet = useApi(() => api.fleet());
  const voyages = useApi(() => api.voyages("ACTIVE"));
  const alerts = useApi(() => api.alerts());
  const recommendations = useApi(() => api.recommendations("PENDING"));
  const vessels = useApi(() => api.vessels());

  const stats = useMemo(() => {
    const f = fleet.data;
    if (!f) return [];
    return [
      { label: "Active voyages", value: num(f.active_voyages), hint: `${f.planned_voyages} planned` },
      {
        label: "Attention required",
        value: num(f.attention_required),
        tone: f.attention_required > 0 ? ("coral" as const) : ("default" as const),
        hint: "ETA slip or consumption overrun",
      },
      {
        label: "Optimization opportunities",
        value: num(f.optimization_opportunities),
        tone: "brass" as const,
        hint: "voyages with a saving on the table",
      },
      {
        label: "Pending approvals",
        value: num(f.pending_approvals),
        hint: "waiting on an operator decision",
      },
      {
        label: "Potential fuel saving",
        value: num(f.potential_fuel_saving_mt),
        unit: "MT",
        tone: "kelp" as const,
        hint: "sum of pending recommendations",
      },
      {
        label: "Potential CO2 saving",
        value: num(f.potential_co2_saving_mt),
        unit: "MT",
        tone: "kelp" as const,
        hint: "IMO / EU MRV emission factors",
      },
    ];
  }, [fleet.data]);

  const markers = (vessels.data ?? []).map((vessel) => ({
    id: `v-${vessel.id}`,
    lon: vessel.longitude,
    lat: vessel.latitude,
    kind: "vessel" as const,
    heading: vessel.heading_deg,
    label: vessel.name,
    detail: `${vessel.vessel_type} · ${num(vessel.current_speed_kn, 1)} kn`,
    onClick: () => router.push(`/vessel?id=${vessel.id}`),
  }));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-medium text-ink">Fleet operations</h1>
          <p className="mt-1 text-xs text-dim">
            Intelligence for every voyage. Figures below are computed by the backend from the
            demo fleet, not estimated by a language model.
          </p>
        </div>
        {fleet.data ? (
          <p className="max-w-[280px] text-right text-2xs text-faint">
            Weather provider{" "}
            <span className="font-mono text-dim">
              {fleet.data.weather_source === "OPEN_METEO" ? "Open-Meteo (auto)" : "mock provider"}
            </span>
            {fleet.data.weather_source === "OPEN_METEO"
              ? ", falling back to the mock provider when it is unreachable"
              : ""}
          </p>
        ) : null}
      </div>

      {fleet.loading ? <Loading label="Loading fleet summary" /> : null}
      {fleet.error ? <ErrorNote message={fleet.error} /> : null}
      {stats.length > 0 ? <StatStrip stats={stats} /> : null}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,2.1fr)_minmax(360px,1fr)]">
        <div className="space-y-4">
          <Panel>
            <PanelHeader
              title="Active voyages"
              caption={`${voyages.data?.length ?? 0} vessels under way`}
            />
            {voyages.loading ? <Loading /> : null}
            {voyages.error ? <ErrorNote message={voyages.error} className="m-4" /> : null}
            {voyages.data ? (
              <VoyageTable
                voyages={voyages.data}
                alerts={alerts.data ?? []}
                showStatus={false}
              />
            ) : null}
          </Panel>

          <Panel className="overflow-hidden">
            <PanelHeader
              title="Fleet chart"
              caption="Live demo positions. Click a vessel to open her file."
            />
            <Map className="h-[420px] w-full" markers={markers} zoom={1.1} center={[60, 20]} />
          </Panel>
        </div>

        <div className="space-y-4">
          <AssistantPanel
            className="h-[440px]"
            intro="Ask about the fleet or a specific voyage. N.A.V. calls the same routing, weather, fuel and optimization tools the UI uses, then explains the result."
            suggestions={[
              "Optimize voyage 1 for minimum fuel",
              "What is the weather on voyage 1?",
              "Compare voyage 1 with the last five voyages",
              "How much fuel can we save?",
            ]}
          />

          <Panel>
            <PanelHeader
              title="N.A.V. recommendations"
              caption="Pending operator decision"
            />
            {recommendations.loading ? <Loading /> : null}
            {recommendations.error ? (
              <ErrorNote message={recommendations.error} className="m-4" />
            ) : null}
            {recommendations.data ? <RecommendationRail items={recommendations.data} /> : null}
          </Panel>
        </div>
      </div>
    </div>
  );
}
