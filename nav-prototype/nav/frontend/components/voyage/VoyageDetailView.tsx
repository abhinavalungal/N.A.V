"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { AssistantPanel } from "@/components/assistant/AssistantPanel";
import { Map } from "@/components/map/Map";
import { OptimizationPanel } from "@/components/optimization/OptimizationPanel";
import { WeatherPanel } from "@/components/voyage/WeatherPanel";
import { RiskBadge, StatusBadge } from "@/components/ui/badge";
import { Field, Panel, PanelHeader } from "@/components/ui/card";
import { ErrorNote, Loading } from "@/components/ui/feedback";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { coord, hours, num, utcDateTime, utcShort } from "@/lib/format";
import type { OptimizationOption, OptimizationRun } from "@/types";

const OPTION_COLORS: Record<string, string> = {
  FASTEST: "#D9634F",
  FUEL_EFFICIENT: "#4FB286",
  WEATHER_OPTIMIZED: "#4C9BC4",
  ECO_SLOW_STEAM: "#B08CD9",
};

export function VoyageDetailView() {
  const search = useSearchParams();
  const id = Number(search.get("id"));
  const voyage = useApi(() => api.voyage(id), [id]);
  const routes = useApi(() => api.voyageRoutes(id), [id]);
  const track = useApi(() => api.trackWeather(id), [id]);
  const [run, setRun] = useState<OptimizationRun | null>(null);
  const [selected, setSelected] = useState<OptimizationOption | null>(null);

  useEffect(() => {
    if (voyage.data?.latest_run) setRun(voyage.data.latest_run);
  }, [voyage.data]);

  const mapRoutes = useMemo(() => {
    const base = voyage.data?.route;
    const lines = [];
    if (base?.geometry?.length) {
      lines.push({
        id: "planned",
        coordinates: base.geometry,
        color: "#33506A",
        width: 2,
        dashed: true,
      });
    }
    (routes.data ?? []).forEach((option) => {
      lines.push({
        id: option.code,
        coordinates: option.geometry,
        color: OPTION_COLORS[option.code] ?? "#4C9BC4",
        width: selected?.code === option.code ? 3 : 1.6,
        opacity: selected && selected.code !== option.code ? 0.35 : 0.9,
      });
    });
    if (selected?.geometry_json?.length) {
      lines.push({
        id: `selected-${selected.id}`,
        coordinates: selected.geometry_json,
        color: OPTION_COLORS[selected.code] ?? "#E3A54B",
        width: 3.4,
      });
    }
    return lines;
  }, [voyage.data, routes.data, selected]);

  const markers = useMemo(() => {
    const v = voyage.data;
    if (!v) return [];
    const pins = [
      {
        id: "origin",
        lon: v.origin_lon,
        lat: v.origin_lat,
        kind: "origin" as const,
        label: v.origin_port,
        detail: `Departed ${utcShort(v.departure_utc)} UTC`,
      },
      {
        id: "destination",
        lon: v.destination_lon,
        lat: v.destination_lat,
        kind: "destination" as const,
        label: v.destination_port,
        detail: `ETA ${utcShort(v.expected_arrival_utc)} UTC`,
      },
    ];
    if (v.current_lat !== null && v.current_lon !== null) {
      pins.push({
        id: "vessel",
        lon: v.current_lon,
        lat: v.current_lat,
        kind: "vessel" as never,
        label: v.vessel.name,
        detail: `${num(v.current_speed_kn, 1)} kn · ${coord(v.current_lat, v.current_lon)}`,
      });
    }
    return pins;
  }, [voyage.data]);

  if (!Number.isFinite(id) || id <= 0)
    return <ErrorNote message="No voyage selected. Open one from the Voyages page." />;
  if (voyage.loading) return <Loading label="Loading voyage" />;
  if (voyage.error) return <ErrorNote message={voyage.error} />;
  if (!voyage.data) return null;

  const v = voyage.data;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-medium">
              {v.origin_port} <span className="text-faint">to</span> {v.destination_port}
            </h1>
            <StatusBadge status={v.status} />
          </div>
          <p className="mt-1 text-xs text-dim">
            <span className="font-mono">{v.reference}</span> ·{" "}
            <Link href={`/vessel?id=${v.vessel_id}`} className="hover:text-brass">
              {v.vessel.name}
            </Link>{" "}
            · IMO <span className="font-mono">{v.vessel.imo}</span> · {v.vessel.vessel_type}
          </p>
        </div>
        <div className="text-right">
          <div className="label">Progress</div>
          <div className="mt-1 flex items-center gap-2">
            <div className="h-1 w-40 bg-deck">
              <div className="h-full bg-sea" style={{ width: `${v.progress_pct}%` }} />
            </div>
            <span className="font-mono tnum text-sm">{num(v.progress_pct, 1)}%</span>
          </div>
        </div>
      </div>

      <section className="grid grid-cols-2 gap-px border border-hairline bg-hairline md:grid-cols-4 xl:grid-cols-8">
        {[
          { label: "Distance", value: `${num(v.distance_nm)} NM` },
          { label: "Remaining", value: `${num(v.distance_remaining_nm)} NM` },
          { label: "Planned speed", value: `${num(v.planned_speed_kn, 1)} kn` },
          { label: "Current speed", value: `${num(v.current_speed_kn, 1)} kn` },
          { label: "Planned fuel", value: `${num(v.planned_fuel_mt, 1)} MT` },
          { label: "Consumed", value: `${num(v.consumed_fuel_mt, 1)} MT` },
          { label: "Departure", value: utcShort(v.departure_utc) },
          { label: "ETA", value: utcShort(v.expected_arrival_utc) },
        ].map((cell) => (
          <div key={cell.label} className="bg-hull px-4 py-3">
            <div className="label">{cell.label}</div>
            <div className="mt-1 font-mono tnum text-sm">{cell.value}</div>
          </div>
        ))}
      </section>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,2.1fr)_minmax(360px,1fr)]">
        <div className="space-y-4">
          <Panel className="overflow-hidden">
            <PanelHeader
              title="Chart"
              caption={
                v.route
                  ? `Sea route via ${v.route.via.join(", ")} · ${num(v.route.distance_nm)} NM`
                  : "Great-circle legs between waypoints"
              }
              actions={
                <div className="flex flex-wrap items-center gap-3 text-2xs text-faint">
                  {(routes.data ?? []).map((option) => (
                    <button
                      key={option.code}
                      onClick={() =>
                        setSelected(
                          selected?.code === option.code
                            ? null
                            : ({
                                ...(selected ?? {}),
                                id: -1,
                                code: option.code,
                                geometry_json: option.geometry,
                              } as OptimizationOption),
                        )
                      }
                      className="flex items-center gap-1.5 hover:text-ink"
                    >
                      <span
                        className="h-0.5 w-4"
                        style={{ background: OPTION_COLORS[option.code] ?? "#4C9BC4" }}
                      />
                      {option.label}
                    </button>
                  ))}
                </div>
              }
            />
            <Map className="h-[460px] w-full" routes={mapRoutes} markers={markers} />
          </Panel>

          <OptimizationPanel
            voyage={v}
            initialRun={run}
            onRun={setRun}
            onSelectOption={setSelected}
            selectedOptionId={selected?.id ?? null}
          />
        </div>

        <div className="space-y-4">
          <Panel>
            <PanelHeader title="Voyage particulars" />
            <div className="grid grid-cols-2 gap-4 p-4">
              <Field label="Vessel" value={v.vessel.name} mono={false} />
              <Field label="Deadweight" value={`${num(v.vessel.deadweight_t)} t`} />
              <Field label="Cargo" value={`${num(v.cargo_t)} t`} />
              <Field label="Fuel type" value={v.vessel.fuel_type} mono={false} />
              <Field label="Design speed" value={`${num(v.vessel.design_speed_kn, 1)} kn`} />
              <Field
                label="Base consumption"
                value={`${num(v.vessel.base_consumption_mt_per_day, 1)} MT/day`}
              />
              <Field label="Position" value={coord(v.current_lat, v.current_lon)} />
              <Field
                label="Required arrival"
                value={v.required_arrival_utc ? utcShort(v.required_arrival_utc) : "none"}
              />
              <Field
                label="Time to ETA"
                value={hours(
                  (new Date(`${v.expected_arrival_utc}Z`).getTime() - Date.now()) / 3600000,
                )}
              />
              <Field label="Departure" value={utcDateTime(v.departure_utc)} />
            </div>
          </Panel>

          <WeatherPanel now={v.weather_now} track={track.data} loading={track.loading} />

          <AssistantPanel
            className="h-[520px]"
            voyageId={v.id}
            suggestions={[
              "Optimize this voyage for minimum fuel",
              "Why did you choose this route?",
              "What happens if I increase speed to 14 knots?",
              "Compare this voyage with the last five voyages",
              "What is the weather on this route?",
            ]}
          />
        </div>
      </div>

      {track.data ? (
        <p className="text-2xs text-faint">
          Weather along the track: mean wind {num(track.data.mean_wind_kn, 1)} kn, mean wave{" "}
          {num(track.data.mean_wave_m, 2)} m, peak wave {num(track.data.max_wave_m, 2)} m, risk{" "}
          index {num(track.data.risk_index, 2)} (<RiskBadge band={track.data.risk_band} />).
        </p>
      ) : null}
    </div>
  );
}
