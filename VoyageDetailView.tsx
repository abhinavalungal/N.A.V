"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AssistantPanel } from "@/components/assistant/AssistantPanel";
import { Map } from "@/components/map/Map";
import { TimeScrubber } from "@/components/map/TimeScrubber";
import { OptimizationPanel } from "@/components/optimization/OptimizationPanel";
import {
  HazardPanel,
  LegSchedule,
  WeatherTimeline,
  conditionWords,
} from "@/components/voyage/LegSchedule";
import { WeatherPanel } from "@/components/voyage/WeatherPanel";
import { Badge, StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, PanelHeader } from "@/components/ui/card";
import { ErrorNote, Loading } from "@/components/ui/feedback";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { coord, num, utcShort } from "@/lib/format";
import { routeColor, token, useTheme } from "@/lib/theme";
import { cn } from "@/lib/utils";
import type { Hazard, OptimizationOption, OptimizationRun, WindField } from "@/types";

function toUtcDate(value: string): Date {
  return new Date(value.endsWith("Z") ? value : `${value}Z`);
}

/** Where the vessel is expected to be at a given moment, along the plan. */
function projected(geometry: number[][], fraction: number): [number, number] | null {
  if (geometry.length < 2) return null;
  const clamped = Math.max(0, Math.min(1, fraction));
  const position = clamped * (geometry.length - 1);
  const i = Math.floor(position);
  const rest = position - i;
  const a = geometry[i];
  const b = geometry[Math.min(geometry.length - 1, i + 1)];
  return [a[0] + (b[0] - a[0]) * rest, a[1] + (b[1] - a[1]) * rest];
}

export function VoyageDetailView() {
  const search = useSearchParams();
  const id = Number(search.get("id"));

  const voyage = useApi(() => api.voyage(id), [id]);
  const plan = useApi(() => api.voyagePlan(id, { legs: 10 }), [id]);
  const track = useApi(() => api.trackWeather(id), [id]);

  const [run, setRun] = useState<OptimizationRun | null>(null);
  const [selectedOption, setSelectedOption] = useState<OptimizationOption | null>(null);
  const [selectedLeg, setSelectedLeg] = useState<number | null>(null);
  const [showWind, setShowWind] = useState(true);
  const [showOptions, setShowOptions] = useState(false);
  const [moment, setMoment] = useState<Date | null>(null);
  const [field, setField] = useState<WindField | null>(null);
  const [theme] = useTheme();

  useEffect(() => {
    if (voyage.data?.latest_run) setRun(voyage.data.latest_run);
  }, [voyage.data]);

  useEffect(() => {
    if (plan.data && moment === null) setMoment(toUtcDate(plan.data.departure_utc));
  }, [plan.data, moment]);

  // The wind grid follows the scrubber, debounced so dragging is not a
  // request per pixel.
  useEffect(() => {
    if (!moment || !showWind || !Number.isFinite(id)) return;
    const timer = setTimeout(() => {
      api
        .windField(id, moment.toISOString().slice(0, 19))
        .then(setField)
        .catch(() => setField(null));
    }, 350);
    return () => clearTimeout(timer);
  }, [id, moment, showWind]);

  const legs = plan.data?.legs ?? [];
  const hazards = plan.data?.hazards ?? [];

  const focusHazard = useCallback((hazard: Hazard) => setMoment(toUtcDate(hazard.start_utc)), []);

  const mapRoutes = useMemo(() => {
    const lines: Array<{
      id: string;
      coordinates: number[][];
      color: string;
      width?: number;
      opacity?: number;
      dashed?: boolean;
    }> = [];
    const base = voyage.data?.route;
    if (base?.geometry?.length) {
      lines.push({ id: "planned", coordinates: base.geometry, color: token("sea"), width: 2.2 });
    }
    if (showOptions && run) {
      run.options
        .filter((o) => o.geometry_json?.length)
        .forEach((option) =>
          lines.push({
            id: `opt-${option.id}`,
            coordinates: option.geometry_json,
            color: routeColor(option.code),
            width: selectedOption?.id === option.id ? 3 : 1.5,
            opacity: selectedOption && selectedOption.id !== option.id ? 0.4 : 0.9,
          }),
        );
    }
    // Heavy weather is drawn over the plan so it reads at a glance.
    hazards.forEach((hazard, i) =>
      lines.push({
        id: `hazard-${i}`,
        coordinates: hazard.geometry,
        color: hazard.severity === "DANGEROUS" ? token("coral") : token("brass"),
        width: 4,
        opacity: 0.9,
      }),
    );
    const leg = legs.find((l) => l.index === selectedLeg);
    if (leg) {
      lines.push({
        id: "selected-leg",
        coordinates: [
          [leg.start[1], leg.start[0]],
          [leg.end[1], leg.end[0]],
        ],
        color: token("brass"),
        width: 5,
        opacity: 0.85,
      });
    }
    return lines;
  }, [voyage.data, run, showOptions, selectedOption, hazards, legs, selectedLeg, theme]);

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

    // The vessel sits where she is expected to be at the scrubbed time.
    const geometry = v.route?.geometry ?? [];
    if (plan.data && moment && geometry.length > 1) {
      const start = toUtcDate(plan.data.departure_utc).getTime();
      const end = toUtcDate(plan.data.arrival_utc).getTime();
      const fraction = end > start ? (moment.getTime() - start) / (end - start) : 0;
      const point = projected(geometry, fraction);
      if (point) {
        pins.push({
          id: "vessel",
          lon: point[0],
          lat: point[1],
          kind: "vessel" as never,
          label: v.vessel.name,
          detail: `Expected position ${utcShort(moment.toISOString())} UTC`,
        });
      }
    } else if (v.current_lat !== null && v.current_lon !== null) {
      pins.push({
        id: "vessel",
        lon: v.current_lon,
        lat: v.current_lat,
        kind: "vessel" as never,
        label: v.vessel.name,
        detail: coord(v.current_lat, v.current_lon),
      });
    }
    return pins;
  }, [voyage.data, plan.data, moment]);

  const windArrows = useMemo(
    () =>
      showWind && field
        ? field.points.map((p) => ({
            lat: p.latitude,
            lon: p.longitude,
            speedKn: p.wind_speed_kn,
            fromDeg: p.wind_direction_deg,
          }))
        : undefined,
    [field, showWind],
  );

  if (!Number.isFinite(id) || id <= 0)
    return <ErrorNote message="No voyage selected. Open one from the Voyages page." />;
  if (voyage.loading) return <Loading label="Loading voyage" />;
  if (voyage.error) return <ErrorNote message={voyage.error} />;
  if (!voyage.data) return null;

  const v = voyage.data;
  const worst = legs.reduce((acc, leg) => Math.max(acc, leg.risk_index), 0);
  const condition = conditionWords(worst);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
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
            · {v.vessel.vessel_type}
          </p>
        </div>
        <Button
          variant={showOptions ? "primary" : "secondary"}
          onClick={() => setShowOptions((s) => !s)}
        >
          {showOptions ? "Hide route options" : "Compare route options"}
        </Button>
      </div>

      {/* The five things an operator checks first. */}
      <section className="grid grid-cols-2 gap-px border border-hairline bg-hairline md:grid-cols-3 xl:grid-cols-6">
        {[
          { label: "Remaining", value: `${num(v.distance_remaining_nm)} NM` },
          { label: "Speed now", value: `${num(v.current_speed_kn, 1)} kn` },
          { label: "ETA", value: `${utcShort(v.expected_arrival_utc)} UTC` },
          { label: "Fuel to go", value: plan.data ? `${num(plan.data.total_fuel_mt, 1)} MT` : "—" },
          { label: "Conditions", value: condition.label, tone: condition.tone },
          {
            label: "Warnings",
            value: hazards.length === 0 ? "None" : String(hazards.length),
            tone: hazards.length > 0 ? "text-coral" : undefined,
          },
        ].map((cell) => (
          <div key={cell.label} className="bg-hull px-4 py-3">
            <div className="label">{cell.label}</div>
            <div className={cn("mt-1 font-mono tnum text-sm", cell.tone ?? "text-ink")}>
              {cell.value}
            </div>
          </div>
        ))}
      </section>

      <div className="grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)_320px]">
        <Panel className="flex max-h-[760px] flex-col">
          <PanelHeader
            title="Passage plan"
            caption={
              plan.data
                ? `${num(plan.data.distance_nm)} NM at ${num(plan.data.speed_kn, 1)} kn`
                : undefined
            }
          />
          {plan.loading ? <Loading label="Building the schedule" /> : null}
          {plan.error ? <ErrorNote message={plan.error} className="m-4" /> : null}
          {plan.data ? (
            <LegSchedule
              legs={legs}
              selected={selectedLeg}
              onSelect={setSelectedLeg}
              origin={v.origin_port}
              destination={v.destination_port}
              arrival={plan.data.arrival_utc}
            />
          ) : null}
        </Panel>

        <div className="space-y-4">
          <Panel className="overflow-hidden">
            <PanelHeader
              title="Chart"
              caption={v.route ? `Via ${v.route.via.join(", ") || "open water"}` : "Great-circle legs"}
              actions={
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowWind((w) => !w)}
                    className={cn(
                      "border px-2 py-1 text-2xs transition-colors",
                      showWind
                        ? "border-sea/50 bg-sea/10 text-sea"
                        : "border-hairline bg-deck text-dim hover:text-ink",
                    )}
                  >
                    Wind
                  </button>
                  {field ? (
                    <Badge tone={field.live_fraction > 0 ? "good" : "brass"}>
                      {field.live_fraction > 0 ? "forecast" : "modelled"}
                    </Badge>
                  ) : null}
                </div>
              }
            />
            <Map
              className="h-[440px] w-full"
              routes={mapRoutes}
              markers={markers}
              wind={windArrows}
            />
            {plan.data ? (
              <TimeScrubber
                from={plan.data.departure_utc}
                to={plan.data.arrival_utc}
                value={moment ?? toUtcDate(plan.data.departure_utc)}
                onChange={setMoment}
              />
            ) : null}
          </Panel>

          {legs.length > 0 ? (
            <Panel>
              <PanelHeader
                title="Conditions along the track"
                caption={
                  plan.data
                    ? plan.data.live_fraction >= 1
                      ? "Live forecast for the whole passage"
                      : plan.data.live_fraction <= 0
                        ? "Modelled: this passage is past the forecast horizon"
                        : `${Math.round(plan.data.live_fraction * 100)}% live forecast, the rest modelled`
                    : undefined
                }
              />
              <WeatherTimeline legs={legs} selected={selectedLeg} onSelect={setSelectedLeg} />
            </Panel>
          ) : null}

          {showOptions ? (
            <OptimizationPanel
              voyage={v}
              initialRun={run}
              onRun={(r) => {
                setRun(r);
                plan.reload();
              }}
              onSelectOption={setSelectedOption}
              selectedOptionId={selectedOption?.id ?? null}
            />
          ) : null}
        </div>

        <div className="space-y-4">
          <HazardPanel hazards={hazards} onFocus={focusHazard} />
          <WeatherPanel now={v.weather_now} track={track.data} loading={track.loading} />
          <AssistantPanel
            className="h-[420px]"
            voyageId={v.id}
            suggestions={[
              "Should I slow down?",
              "Why is the weather a problem here?",
              "What happens at 14 knots?",
              "How does this compare with our last voyages?",
            ]}
          />
        </div>
      </div>
    </div>
  );
}
