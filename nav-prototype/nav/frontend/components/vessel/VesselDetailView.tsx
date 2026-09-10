"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { PredictedVsActualChart } from "@/components/analytics/Charts";
import { VoyageTable } from "@/components/dashboard/VoyageTable";
import { Map } from "@/components/map/Map";
import { Badge } from "@/components/ui/badge";
import { Field, Panel, PanelHeader } from "@/components/ui/card";
import { Empty, ErrorNote, Loading } from "@/components/ui/feedback";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { coord, num, signed, utcShort } from "@/lib/format";

export function VesselDetailView() {
  const search = useSearchParams();
  const id = Number(search.get("id"));
  const vessel = useApi(() => api.vessel(id), [id]);
  const history = useApi(() => api.vesselHistory(id, 12), [id]);

  if (!Number.isFinite(id) || id <= 0)
    return <ErrorNote message="No vessel selected. Open one from the Vessels page." />;
  if (vessel.loading) return <Loading label="Loading vessel" />;
  if (vessel.error) return <ErrorNote message={vessel.error} />;
  if (!vessel.data) return null;

  const v = vessel.data;
  const chartData = (history.data?.voyages ?? [])
    .slice()
    .reverse()
    .map((voyage) => ({
      label: `${voyage.origin_port.slice(0, 3).toUpperCase()}–${voyage.destination_port
        .slice(0, 3)
        .toUpperCase()}`,
      predicted: voyage.predicted_fuel_mt,
      actual: voyage.actual_fuel_mt,
    }));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-medium">{v.name}</h1>
            <Badge tone={v.status === "AT_SEA" ? "active" : "neutral"}>{v.status}</Badge>
          </div>
          <p className="mt-1 text-xs text-dim">
            IMO <span className="font-mono">{v.imo}</span> · {v.vessel_type} · built{" "}
            <span className="font-mono">{v.year_built}</span>
            {v.company ? ` · ${v.company.name}` : ""}
          </p>
        </div>
        {v.current_voyage ? (
          <Link
            href={`/voyage?id=${v.current_voyage.id}`}
            className="text-xs text-brass hover:underline"
          >
            Open current voyage {v.current_voyage.reference}
          </Link>
        ) : null}
      </div>

      <section className="grid grid-cols-2 gap-px border border-hairline bg-hairline md:grid-cols-4 xl:grid-cols-7">
        {[
          { label: "Deadweight", value: `${num(v.deadweight_t)} t` },
          { label: "Design speed", value: `${num(v.design_speed_kn, 1)} kn` },
          { label: "Current speed", value: `${num(v.current_speed_kn, 1)} kn` },
          { label: "Base consumption", value: `${num(v.base_consumption_mt_per_day, 1)} MT/d` },
          { label: "Fuel type", value: v.fuel_type },
          { label: "Heading", value: `${num(v.heading_deg)}°` },
          { label: "Position", value: coord(v.latitude, v.longitude) },
        ].map((cell) => (
          <div key={cell.label} className="bg-hull px-4 py-3">
            <div className="label">{cell.label}</div>
            <div className="mt-1 font-mono tnum text-sm">{cell.value}</div>
          </div>
        ))}
      </section>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <Panel className="overflow-hidden">
          <PanelHeader title="Position" caption="Demo AIS position from the seeded database" />
          <Map
            className="h-[300px] w-full"
            markers={[
              {
                id: "vessel",
                lon: v.longitude,
                lat: v.latitude,
                kind: "vessel",
                heading: v.heading_deg,
                label: v.name,
                detail: coord(v.latitude, v.longitude),
              },
            ]}
            center={[v.longitude, v.latitude]}
            zoom={3}
          />
        </Panel>

        <Panel>
          <PanelHeader
            title="Historical performance"
            caption={
              history.data
                ? `${history.data.sample_size} completed voyages`
                : "Loading history"
            }
          />
          {history.loading ? <Loading /> : null}
          {history.data ? (
            <div className="grid grid-cols-2 gap-4 p-4 sm:grid-cols-4">
              <Field label="Average speed" value={`${num(history.data.average_speed_kn, 1)} kn`} />
              <Field label="Average fuel" value={`${num(history.data.average_fuel_mt, 1)} MT`} />
              <Field
                label="Fuel variance"
                value={
                  <span
                    className={
                      history.data.average_fuel_variance_pct > 0 ? "text-coral" : "text-kelp"
                    }
                  >
                    {signed(history.data.average_fuel_variance_pct, 1, "%")}
                  </span>
                }
              />
              <Field
                label="ETA variance"
                value={signed(history.data.average_eta_variance_hours, 1, " h")}
              />
            </div>
          ) : null}
          {chartData.length > 0 ? (
            <div className="border-t border-hairline p-3">
              <PredictedVsActualChart data={chartData} />
              <p className="px-1 pt-1 text-2xs text-faint">
                Predicted against actual fuel burn per completed voyage, oldest on the left.
              </p>
            </div>
          ) : (
            <Empty>No completed voyages recorded for this vessel.</Empty>
          )}
        </Panel>
      </div>

      <Panel>
        <PanelHeader title="Recent voyages" caption="Most recent first" />
        {v.recent_voyages.length > 0 ? (
          <VoyageTable voyages={v.recent_voyages} />
        ) : (
          <Empty>No voyages recorded.</Empty>
        )}
      </Panel>

      {history.data && history.data.voyages.length > 0 ? (
        <Panel>
          <PanelHeader
            title="Completed voyage log"
            caption="Historical records used by the assistant when you ask it to compare"
          />
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] border-collapse text-xs">
              <thead>
                <tr className="border-b border-hairline text-left text-2xs text-faint">
                  <th className="px-4 py-2.5 font-normal">Reference</th>
                  <th className="px-4 py-2.5 font-normal">Route</th>
                  <th className="px-4 py-2.5 text-right font-normal">Arrived</th>
                  <th className="px-4 py-2.5 text-right font-normal">Distance</th>
                  <th className="px-4 py-2.5 text-right font-normal">Speed</th>
                  <th className="px-4 py-2.5 text-right font-normal">Predicted</th>
                  <th className="px-4 py-2.5 text-right font-normal">Actual</th>
                  <th className="px-4 py-2.5 text-right font-normal">CO2</th>
                </tr>
              </thead>
              <tbody>
                {history.data.voyages.map((row) => (
                  <tr key={row.id} className="border-b border-hairline/60 last:border-0">
                    <td className="px-4 py-2.5 font-mono tnum text-dim">{row.reference}</td>
                    <td className="px-4 py-2.5 text-dim">
                      {row.origin_port} <span className="text-faint">to</span> {row.destination_port}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono tnum text-dim">
                      {utcShort(row.arrival_utc)}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono tnum text-dim">
                      {num(row.distance_nm)} NM
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono tnum text-dim">
                      {num(row.average_speed_kn, 1)} kn
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono tnum text-dim">
                      {num(row.predicted_fuel_mt, 1)}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono tnum text-ink">
                      {num(row.actual_fuel_mt, 1)}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono tnum text-dim">
                      {num(row.co2_mt, 1)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      ) : null}
    </div>
  );
}
