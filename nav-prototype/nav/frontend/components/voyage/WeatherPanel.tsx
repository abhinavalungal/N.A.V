"use client";

import { Panel, PanelHeader } from "@/components/ui/card";
import { Badge, RiskBadge } from "@/components/ui/badge";
import { Loading } from "@/components/ui/feedback";
import { num, utcShort } from "@/lib/format";
import type { RouteWeather, Weather } from "@/types";

function compass(deg: number): string {
  const points = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
  return points[Math.round(deg / 22.5) % 16];
}

export function WeatherPanel({
  now,
  track,
  loading,
}: {
  now: Weather | null;
  track?: RouteWeather | null;
  loading?: boolean;
}) {
  return (
    <Panel>
      <PanelHeader
        title="Weather"
        caption={now ? `Valid ${utcShort(now.valid_at)} UTC` : undefined}
        actions={
          now ? (
            <Badge tone={now.is_live ? "good" : "brass"}>
              {now.is_live ? "Open-Meteo" : "Mock data"}
            </Badge>
          ) : null
        }
      />
      {loading && !now ? <Loading label="Sampling the route" /> : null}
      {now ? (
        <div className="grid grid-cols-2 gap-4 p-4">
          <Cell
            label="Wind"
            value={`${num(now.wind_speed_kn, 1)} kn`}
            sub={`from ${compass(now.wind_direction_deg)} ${num(now.wind_direction_deg)}°`}
          />
          <Cell
            label="Waves"
            value={`${num(now.wave_height_m, 2)} m`}
            sub={
              now.wave_period_s
                ? `from ${compass(now.wave_direction_deg)} · ${num(now.wave_period_s, 1)} s`
                : `from ${compass(now.wave_direction_deg)}`
            }
          />
          <Cell
            label="Current"
            value={`${num(now.current_speed_kn, 2)} kn`}
            sub={`setting ${compass(now.current_direction_deg)}`}
          />
          <Cell
            label="Visibility"
            value={`${num(now.visibility_nm, 1)} NM`}
            sub={`${num(now.temperature_c, 1)} °C`}
          />
          {now.swell_wave_height_m !== null ? (
            <Cell label="Swell" value={`${num(now.swell_wave_height_m, 2)} m`} />
          ) : null}
        </div>
      ) : null}

      {track ? (
        <div className="space-y-3 border-t border-hairline p-4">
          <div className="flex items-center justify-between">
            <span className="label">Along the remaining track</span>
            <RiskBadge band={track.risk_band} />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Cell label="Mean wind" value={`${num(track.mean_wind_kn, 1)} kn`} />
            <Cell label="Mean wave" value={`${num(track.mean_wave_m, 2)} m`} />
            <Cell label="Peak wave" value={`${num(track.max_wave_m, 2)} m`} />
          </div>
          <Sparkline samples={track.samples} />
          <p className="text-2xs text-faint">
            {track.samples.length} sample points ·{" "}
            {track.live_fraction >= 1
              ? "all live"
              : track.live_fraction <= 0
                ? "no live coverage"
                : `${Math.round(track.live_fraction * 100)}% live, the rest beyond the forecast horizon`}{" "}
            · source{" "}
            {track.source === "OPEN_METEO" ? (
              <>
                <a
                  href="https://open-meteo.com/"
                  target="_blank"
                  rel="noreferrer noopener"
                  className="underline decoration-dotted hover:text-dim"
                >
                  Open-Meteo
                </a>{" "}
                marine forecast, data under{" "}
                <a
                  href="https://creativecommons.org/licenses/by/4.0/"
                  target="_blank"
                  rel="noreferrer noopener"
                  className="underline decoration-dotted hover:text-dim"
                >
                  CC BY 4.0
                </a>
              </>
            ) : (
              "deterministic mock provider"
            )}
          </p>
        </div>
      ) : null}
    </Panel>
  );
}

function Cell({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div>
      <div className="label">{label}</div>
      <div className="mt-1 font-mono tnum text-sm text-ink">{value}</div>
      {sub ? <div className="mt-0.5 text-2xs text-faint">{sub}</div> : null}
    </div>
  );
}

/** Wave height profile along the track, drawn as a plain area sparkline. */
function Sparkline({ samples }: { samples: Weather[] }) {
  if (samples.length < 2) return null;
  const heights = samples.map((s) => s.wave_height_m);
  const max = Math.max(...heights, 1);
  const points = heights
    .map((h, i) => `${(i / (heights.length - 1)) * 100},${32 - (h / max) * 30}`)
    .join(" ");
  return (
    <div>
      <svg viewBox="0 0 100 32" preserveAspectRatio="none" className="h-12 w-full">
        <polyline points={`0,32 ${points} 100,32`} fill="rgb(var(--sea) / 0.16)" stroke="none" />
        <polyline points={points} fill="none" stroke="rgb(var(--sea))" strokeWidth="0.8" vectorEffect="non-scaling-stroke" />
      </svg>
      <div className="flex justify-between text-2xs text-faint">
        <span>departure</span>
        <span>peak {num(max, 2)} m</span>
        <span>arrival</span>
      </div>
    </div>
  );
}
