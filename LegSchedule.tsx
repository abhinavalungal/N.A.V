"use client";

import { AlertTriangle, Wind } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Panel, PanelHeader } from "@/components/ui/card";
import { Empty } from "@/components/ui/feedback";
import { num, utcShort } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Hazard, Leg } from "@/types";

/** Small arrow showing where wind, sea or current is coming from. */
function DirectionArrow({ deg, className }: { deg: number; className?: string }) {
  return (
    <svg
      viewBox="0 0 12 12"
      className={cn("h-3 w-3 shrink-0", className)}
      style={{ transform: `rotate(${deg + 180}deg)` }}
      aria-hidden
    >
      <path d="M6 1 L6 11 M6 11 L3.2 7.6 M6 11 L8.8 7.6" stroke="currentColor" strokeWidth="1.3" fill="none" />
    </svg>
  );
}

function windTone(kn: number) {
  if (kn >= 48) return "text-coral";
  if (kn >= 34) return "text-brass";
  return "text-dim";
}

function seaTone(m: number) {
  if (m >= 6) return "text-coral";
  if (m >= 4) return "text-brass";
  return "text-dim";
}

/** Plain words instead of a risk index. */
export function conditionWords(risk: number): { label: string; tone: string } {
  if (risk >= 0.66) return { label: "Rough", tone: "text-coral" };
  if (risk >= 0.4) return { label: "Moderate", tone: "text-brass" };
  return { label: "Good", tone: "text-kelp" };
}

/**
 * The passage as a list of legs: when the vessel is where, how far, how fast,
 * and what it burns. Clicking one selects it on the chart.
 */
export function LegSchedule({
  legs,
  selected,
  onSelect,
  origin,
  destination,
  arrival,
}: {
  legs: Leg[];
  selected: number | null;
  onSelect: (index: number | null) => void;
  origin: string;
  destination: string;
  arrival?: string;
}) {
  if (legs.length === 0) return <Empty>No schedule for this voyage yet.</Empty>;

  return (
    <div className="flex min-h-0 flex-col">
      <div className="border-b border-hairline px-4 py-3">
        <div className="label">Depart</div>
        <div className="mt-0.5 text-sm text-ink">{origin}</div>
        <div className="mt-0.5 font-mono tnum text-2xs text-faint">
          {utcShort(legs[0].depart_utc)} UTC
        </div>
      </div>

      <ol className="min-h-0 flex-1 overflow-y-auto">
        {legs.map((leg) => {
          const condition = conditionWords(leg.risk_index);
          const active = selected === leg.index;
          return (
            <li key={leg.index}>
              <button
                onClick={() => onSelect(active ? null : leg.index)}
                className={cn(
                  "w-full border-b border-hairline/70 px-4 py-3 text-left transition-colors hover:bg-deck",
                  active && "bg-deck",
                )}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      "flex h-5 w-5 shrink-0 items-center justify-center rounded-sm border font-mono text-2xs",
                      active
                        ? "border-brass bg-brass text-abyss"
                        : "border-hairline bg-hull text-dim",
                    )}
                  >
                    {leg.index}
                  </span>
                  <span className="font-mono tnum text-xs text-ink">
                    {utcShort(leg.arrive_utc)} UTC
                  </span>
                  <span className={cn("ml-auto text-2xs", condition.tone)}>{condition.label}</span>
                </div>

                <div className="mt-2 grid grid-cols-3 gap-2 font-mono tnum text-2xs text-dim">
                  <span>{num(leg.distance_nm)} NM</span>
                  <span>{num(leg.speed_kn, 1)} kn</span>
                  <span>{num(leg.fuel_mt, 1)} MT</span>
                </div>

                <div className="mt-2 flex items-center gap-3 text-2xs text-faint">
                  <span className={cn("flex items-center gap-1", windTone(leg.wind_speed_kn))}>
                    <DirectionArrow deg={leg.wind_direction_deg} />
                    {num(leg.wind_speed_kn, 0)} kn
                  </span>
                  <span className={cn("flex items-center gap-1", seaTone(leg.wave_height_m))}>
                    <DirectionArrow deg={leg.wave_direction_deg} />
                    {num(leg.wave_height_m, 1)} m
                  </span>
                  <span className="font-mono">{leg.weather_source === "OPEN_METEO" ? "live" : "mock"}</span>
                </div>
              </button>
            </li>
          );
        })}
      </ol>

      <div className="border-t border-hairline px-4 py-3">
        <div className="label">Arrive</div>
        <div className="mt-0.5 text-sm text-ink">{destination}</div>
        <div className="mt-0.5 font-mono tnum text-2xs text-faint">
          {utcShort(arrival ?? legs[legs.length - 1].arrive_utc)} UTC
        </div>
      </div>
    </div>
  );
}

/**
 * Conditions along the track, one column per leg. Same information a router's
 * weather strip carries: wind, sea, swell proxy, current, and the speed held.
 */
export function WeatherTimeline({
  legs,
  selected,
  onSelect,
}: {
  legs: Leg[];
  selected: number | null;
  onSelect: (index: number | null) => void;
}) {
  if (legs.length === 0) return null;

  const rows = [
    {
      key: "wind",
      label: "Wind",
      render: (leg: Leg) => (
        <span className={cn("flex items-center justify-center gap-1", windTone(leg.wind_speed_kn))}>
          <DirectionArrow deg={leg.wind_direction_deg} />
          {num(leg.wind_speed_kn, 0)}
        </span>
      ),
      unit: "kn",
    },
    {
      key: "sea",
      label: "Sea",
      render: (leg: Leg) => (
        <span className={cn("flex items-center justify-center gap-1", seaTone(leg.wave_height_m))}>
          <DirectionArrow deg={leg.wave_direction_deg} />
          {num(leg.wave_height_m, 1)}
        </span>
      ),
      unit: "m",
    },
    {
      key: "current",
      label: "Current",
      render: (leg: Leg) => (
        <span className="text-dim">{num(leg.current_speed_kn, 1)}</span>
      ),
      unit: "kn",
    },
    {
      key: "speed",
      label: "Speed",
      render: (leg: Leg) => <span className="text-dim">{num(leg.speed_kn, 1)}</span>,
      unit: "kn",
    },
    {
      key: "fuel",
      label: "Fuel",
      render: (leg: Leg) => <span className="text-dim">{num(leg.fuel_mt, 1)}</span>,
      unit: "MT",
    },
  ];

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] border-collapse text-2xs">
        <thead>
          <tr>
            <th className="sticky left-0 z-10 bg-hull px-3 py-2 text-left font-normal text-faint">
              Along the track
            </th>
            {legs.map((leg) => (
              <th
                key={leg.index}
                onClick={() => onSelect(selected === leg.index ? null : leg.index)}
                className={cn(
                  "cursor-pointer border-l border-hairline px-2 py-2 font-normal transition-colors hover:bg-deck",
                  selected === leg.index ? "bg-deck text-ink" : "text-faint",
                )}
              >
                <div className="font-mono tnum">{utcShort(leg.arrive_utc).slice(0, 6)}</div>
                <div className="font-mono tnum text-faint">
                  {utcShort(leg.arrive_utc).slice(7)}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key} className="border-t border-hairline/60">
              <td className="sticky left-0 z-10 bg-hull px-3 py-1.5 text-faint">
                {row.label} <span className="text-faint/70">{row.unit}</span>
              </td>
              {legs.map((leg) => (
                <td
                  key={leg.index}
                  className={cn(
                    "border-l border-hairline/60 px-2 py-1.5 text-center font-mono tnum",
                    selected === leg.index && "bg-deck",
                  )}
                >
                  {row.render(leg)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Heavy-weather windows, in the words an operator would use. */
export function HazardPanel({
  hazards,
  onFocus,
}: {
  hazards: Hazard[];
  onFocus?: (hazard: Hazard) => void;
}) {
  return (
    <Panel>
      <PanelHeader
        title="Weather warnings"
        caption={
          hazards.length === 0
            ? "Nothing above gale force on this track"
            : `${hazards.length} window${hazards.length > 1 ? "s" : ""} to plan around`
        }
        actions={<Wind className="h-3.5 w-3.5 text-faint" />}
      />
      {hazards.length === 0 ? (
        <Empty>The forecast stays below 34 kn and 4 m for the whole passage.</Empty>
      ) : (
        <ul className="divide-y divide-hairline">
          {hazards.map((hazard, i) => (
            <li key={i}>
              <button
                onClick={() => onFocus?.(hazard)}
                className="w-full px-4 py-3 text-left transition-colors hover:bg-deck"
              >
                <div className="flex items-center gap-2">
                  <AlertTriangle
                    className={cn(
                      "h-3.5 w-3.5",
                      hazard.severity === "DANGEROUS" ? "text-coral" : "text-brass",
                    )}
                  />
                  <span className="text-xs text-ink">
                    {hazard.severity === "DANGEROUS" ? "Dangerous weather" : "Rough weather"}
                  </span>
                  <Badge
                    tone={hazard.severity === "DANGEROUS" ? "alert" : "brass"}
                    className="ml-auto"
                  >
                    {hazard.source === "OPEN_METEO" ? "forecast" : "modelled"}
                  </Badge>
                </div>
                <p className="mt-1.5 text-2xs text-dim">
                  {hazard.reason.charAt(0).toUpperCase() + hazard.reason.slice(1)}
                </p>
                <p className="mt-1 font-mono tnum text-2xs text-faint">
                  {utcShort(hazard.start_utc)} to {utcShort(hazard.end_utc)} UTC
                </p>
              </button>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
