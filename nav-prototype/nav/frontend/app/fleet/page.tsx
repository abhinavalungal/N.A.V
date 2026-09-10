"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { Map } from "@/components/map/Map";
import { Badge } from "@/components/ui/badge";
import { Panel, PanelHeader } from "@/components/ui/card";
import { ErrorNote, Loading } from "@/components/ui/feedback";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { coord, num, utcShort } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Voyage } from "@/types";

export default function FleetPage() {
  const router = useRouter();
  const vessels = useApi(() => api.vessels());
  const voyages = useApi(() => api.voyages("ACTIVE"));
  const alerts = useApi(() => api.alerts());
  const [focus, setFocus] = useState<number | null>(null);

  const voyageByVessel = useMemo(() => {
    const index: Record<number, Voyage> = {};
    (voyages.data ?? []).forEach((v) => {
      index[v.vessel_id] = v;
    });
    return index;
  }, [voyages.data]);

  const markers = (vessels.data ?? []).map((vessel) => ({
    id: `v-${vessel.id}`,
    lon: vessel.longitude,
    lat: vessel.latitude,
    kind: "vessel" as const,
    heading: vessel.heading_deg,
    muted: focus !== null && focus !== vessel.id,
    label: vessel.name,
    detail: `${vessel.vessel_type} · ${num(vessel.current_speed_kn, 1)} kn`,
    onClick: () => setFocus(vessel.id),
  }));

  const focused = vessels.data?.find((v) => v.id === focus) ?? null;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-medium">Fleet</h1>
        <p className="mt-1 text-xs text-dim">
          Positions, active voyages and open alerts for the whole demo fleet.
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(340px,1fr)]">
        <Panel className="overflow-hidden">
          <PanelHeader
            title="Chart"
            caption={`${vessels.data?.length ?? 0} vessels`}
            actions={
              focused ? (
                <button
                  onClick={() => setFocus(null)}
                  className="text-2xs text-faint hover:text-ink"
                >
                  Clear focus
                </button>
              ) : null
            }
          />
          <Map
            className="h-[560px] w-full"
            markers={markers}
            center={focused ? [focused.longitude, focused.latitude] : [60, 20]}
            zoom={focused ? 3.4 : 1.1}
          />
        </Panel>

        <Panel className="flex max-h-[620px] flex-col">
          <PanelHeader title="Vessels" caption="Click to focus the chart" />
          {vessels.loading ? <Loading /> : null}
          {vessels.error ? <ErrorNote message={vessels.error} className="m-4" /> : null}
          <div className="min-h-0 flex-1 divide-y divide-hairline overflow-y-auto">
            {(vessels.data ?? []).map((vessel) => {
              const voyage = voyageByVessel[vessel.id];
              const alert = (alerts.data ?? []).find((a) => a.voyage_id === voyage?.id);
              return (
                <button
                  key={vessel.id}
                  onClick={() => setFocus(vessel.id)}
                  onDoubleClick={() => router.push(`/vessel?id=${vessel.id}`)}
                  className={cn(
                    "block w-full px-4 py-3 text-left transition-colors hover:bg-deck",
                    focus === vessel.id && "bg-deck",
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm text-ink">{vessel.name}</span>
                    <Badge tone={vessel.status === "AT_SEA" ? "active" : "neutral"}>
                      {vessel.status}
                    </Badge>
                  </div>
                  <p className="mt-1 font-mono tnum text-2xs text-faint">
                    {coord(vessel.latitude, vessel.longitude)} · {num(vessel.current_speed_kn, 1)} kn
                  </p>
                  {voyage ? (
                    <p className="mt-1.5 text-2xs text-dim">
                      {voyage.origin_port} to {voyage.destination_port} · ETA{" "}
                      <span className="font-mono">{utcShort(voyage.expected_arrival_utc)}</span>
                    </p>
                  ) : (
                    <p className="mt-1.5 text-2xs text-faint">No active voyage</p>
                  )}
                  {alert ? (
                    <p
                      className={cn(
                        "mt-1.5 text-2xs",
                        alert.severity === "ACTION" ? "text-coral" : "text-brass",
                      )}
                    >
                      {alert.message}
                    </p>
                  ) : null}
                </button>
              );
            })}
          </div>
        </Panel>
      </div>
    </div>
  );
}
