"use client";

import { useEffect, useMemo, useState } from "react";

import { AssistantPanel } from "@/components/assistant/AssistantPanel";
import { Map } from "@/components/map/Map";
import { OptimizationPanel } from "@/components/optimization/OptimizationPanel";
import { StatusBadge } from "@/components/ui/badge";
import { Panel, PanelHeader } from "@/components/ui/card";
import { Select } from "@/components/ui/controls";
import { Empty, ErrorNote, Loading } from "@/components/ui/feedback";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { routeColor, token, useTheme } from "@/lib/theme";
import { num, utcShort } from "@/lib/format";
import type { OptimizationOption, OptimizationRun, VoyageDetail } from "@/types";

export default function OptimizationPage() {
  const voyages = useApi(() => api.voyages());
  const recommendations = useApi(() => api.recommendations());
  const [voyageId, setVoyageId] = useState<number | null>(null);
  const [detail, setDetail] = useState<VoyageDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [run, setRun] = useState<OptimizationRun | null>(null);
  const [selected, setSelected] = useState<OptimizationOption | null>(null);
  const [theme] = useTheme();

  const candidates = useMemo(
    () => (voyages.data ?? []).filter((v) => v.status !== "COMPLETED"),
    [voyages.data],
  );

  useEffect(() => {
    if (voyageId === null && candidates.length > 0) setVoyageId(candidates[0].id);
  }, [candidates, voyageId]);

  useEffect(() => {
    if (voyageId === null) return;
    setDetail(null);
    setRun(null);
    setSelected(null);
    setDetailError(null);
    api
      .voyage(voyageId)
      .then((d) => {
        setDetail(d);
        setRun(d.latest_run);
      })
      .catch((e) => setDetailError(e instanceof Error ? e.message : "Could not load voyage"));
  }, [voyageId]);

  const mapRoutes = useMemo(() => {
    if (!run) {
      return detail?.route?.geometry?.length
        ? [{ id: "planned", coordinates: detail.route.geometry, color: token("faint"), width: 2, dashed: true }]
        : [];
    }
    return run.options
      .filter((option) => option.geometry_json?.length)
      .map((option) => ({
        id: `opt-${option.id}`,
        coordinates: option.geometry_json,
        color: routeColor(option.code),
        width: selected?.id === option.id ? 3.2 : option.recommended ? 2.4 : 1.5,
        opacity: selected && selected.id !== option.id ? 0.4 : 0.95,
      }));
  }, [run, detail, selected, theme]);

  const markers = detail
    ? [
        {
          id: "origin",
          lon: detail.origin_lon,
          lat: detail.origin_lat,
          kind: "origin" as const,
          label: detail.origin_port,
        },
        {
          id: "destination",
          lon: detail.destination_lon,
          lat: detail.destination_lat,
          kind: "destination" as const,
          label: detail.destination_port,
        },
      ]
    : [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-medium">Optimization</h1>
          <p className="mt-1 text-xs text-dim">
            Four route variants are evaluated against real routing, weather and fuel models. The
            recommendation is whichever scores lowest for your objective.
          </p>
        </div>
        <label className="flex items-center gap-2 text-xs text-dim">
          Voyage
          <Select
            className="w-[420px] font-sans"
            value={voyageId ?? ""}
            onChange={(e) => setVoyageId(Number(e.target.value))}
          >
            {candidates.map((voyage) => (
              <option key={voyage.id} value={voyage.id}>
                {voyage.reference} · {voyage.vessel_name} · {voyage.origin_port} to{" "}
                {voyage.destination_port}
              </option>
            ))}
          </Select>
        </label>
      </div>

      {voyages.error ? <ErrorNote message={voyages.error} /> : null}
      {detailError ? <ErrorNote message={detailError} /> : null}
      {!detail && !detailError ? <Loading label="Loading voyage" /> : null}

      {detail ? (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,2.1fr)_minmax(360px,1fr)]">
          <div className="space-y-4">
            <Panel className="overflow-hidden">
              <PanelHeader
                title="Route options"
                caption={
                  run
                    ? "Click an option card below to highlight it on the chart"
                    : "Planned route. Run the optimizer to compare variants."
                }
              />
              <Map className="h-[380px] w-full" routes={mapRoutes} markers={markers} />
            </Panel>

            <OptimizationPanel
              voyage={detail}
              initialRun={run}
              onRun={(r) => {
                setRun(r);
                recommendations.reload();
              }}
              onSelectOption={setSelected}
              selectedOptionId={selected?.id ?? null}
            />
          </div>

          <div className="space-y-4">
            <AssistantPanel
              className="h-[420px]"
              voyageId={detail.id}
              suggestions={[
                "Optimize this voyage for minimum fuel",
                "Why did you choose this route?",
                "What happens if I increase speed to 14 knots?",
              ]}
            />

            <Panel>
              <PanelHeader title="Approval history" caption="Across the fleet" />
              {recommendations.loading ? <Loading /> : null}
              {(recommendations.data ?? []).length === 0 ? (
                <Empty>No recommendations recorded yet.</Empty>
              ) : (
                <ul className="max-h-[420px] divide-y divide-hairline overflow-y-auto">
                  {(recommendations.data ?? []).map((rec) => (
                    <li key={rec.id} className="px-4 py-3">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs text-ink">{rec.vessel_name}</span>
                        <StatusBadge status={rec.status} />
                      </div>
                      <p className="mt-1 text-2xs text-faint">
                        <span className="font-mono">{rec.voyage_reference}</span> · {rec.route_label}{" "}
                        · saves <span className="font-mono">{num(rec.fuel_saving_mt, 1)}</span> MT ·{" "}
                        {utcShort(rec.created_at)}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          </div>
        </div>
      ) : null}
    </div>
  );
}
