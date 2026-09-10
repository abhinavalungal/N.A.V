"use client";

import { EmissionsChart, FuelByVesselChart, PredictedVsActualChart } from "@/components/analytics/Charts";
import { StatStrip } from "@/components/dashboard/StatStrip";
import { Panel, PanelHeader } from "@/components/ui/card";
import { Empty, ErrorNote, Loading } from "@/components/ui/feedback";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { num } from "@/lib/format";

export default function AnalyticsPage() {
  const fleet = useApi(() => api.fleet());
  const prices = useApi(() => api.fuelPrices());

  if (fleet.loading) return <Loading label="Loading analytics" />;
  if (fleet.error) return <ErrorNote message={fleet.error} />;
  if (!fleet.data) return null;

  const f = fleet.data;
  const monthly = f.monthly_performance.map((row) => ({
    label: row.month,
    predicted: row.predicted_fuel_mt,
    actual: row.actual_fuel_mt,
  }));

  const totalPredicted = f.monthly_performance.reduce((a, r) => a + r.predicted_fuel_mt, 0);
  const totalActual = f.monthly_performance.reduce((a, r) => a + r.actual_fuel_mt, 0);
  const accuracy =
    totalPredicted > 0 ? ((totalActual - totalPredicted) / totalPredicted) * 100 : 0;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-medium">Analytics</h1>
        <p className="mt-1 text-xs text-dim">
          Fleet totals from active voyages, and prediction accuracy from the completed voyage log.
        </p>
      </div>

      <StatStrip
        stats={[
          { label: "Fleet fuel on plan", value: num(f.fleet_fuel_mt), unit: "MT" },
          { label: "Fleet CO2", value: num(f.fleet_co2_mt), unit: "MT" },
          {
            label: "Approved savings",
            value: num(f.approved_fuel_saving_mt, 1),
            unit: "MT",
            tone: "kelp",
          },
          {
            label: "Pending savings",
            value: num(f.potential_fuel_saving_mt, 1),
            unit: "MT",
            tone: "brass",
          },
          {
            label: "Model bias",
            value: `${accuracy > 0 ? "+" : ""}${accuracy.toFixed(1)}`,
            unit: "%",
            hint: "actual against predicted fuel",
            tone: Math.abs(accuracy) > 5 ? "coral" : "default",
          },
          {
            label: "Completed voyages",
            value: num(f.completed_voyages),
            hint: `${f.planned_voyages} planned`,
          },
        ]}
      />

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel>
          <PanelHeader
            title="Fuel by vessel"
            caption="Planned against consumed on current active voyages"
          />
          <div className="p-3">
            {f.fuel_by_vessel.length > 0 ? (
              <FuelByVesselChart data={f.fuel_by_vessel} />
            ) : (
              <Empty>No active voyages.</Empty>
            )}
          </div>
        </Panel>

        <Panel>
          <PanelHeader
            title="Predicted against actual fuel"
            caption="Monthly totals from the completed voyage log"
          />
          <div className="p-3">
            {monthly.length > 0 ? (
              <PredictedVsActualChart data={monthly} />
            ) : (
              <Empty>No completed voyages recorded.</Empty>
            )}
          </div>
        </Panel>

        <Panel>
          <PanelHeader title="CO2 by month" caption="IMO / EU MRV emission factors" />
          <div className="p-3">
            {f.monthly_performance.length > 0 ? (
              <EmissionsChart data={f.monthly_performance} />
            ) : (
              <Empty>No completed voyages recorded.</Empty>
            )}
          </div>
        </Panel>

        <Panel>
          <PanelHeader
            title="Bunker prices"
            caption="Demo prices seeded into the database, not a live market feed"
          />
          {prices.loading ? <Loading /> : null}
          <div className="max-h-[320px] overflow-y-auto">
            <table className="w-full border-collapse text-xs">
              <thead>
                <tr className="border-b border-hairline text-left text-2xs text-faint">
                  <th className="px-4 py-2.5 font-normal">Port</th>
                  <th className="px-4 py-2.5 font-normal">Fuel</th>
                  <th className="px-4 py-2.5 text-right font-normal">USD/MT</th>
                  <th className="px-4 py-2.5 font-normal">Source</th>
                </tr>
              </thead>
              <tbody>
                {(prices.data ?? []).map((price, i) => (
                  <tr key={i} className="border-b border-hairline/60 last:border-0">
                    <td className="px-4 py-2 text-dim">{price.port}</td>
                    <td className="px-4 py-2 text-dim">{price.fuel_type}</td>
                    <td className="px-4 py-2 text-right font-mono tnum text-ink">
                      {num(price.price_usd_per_mt)}
                    </td>
                    <td className="px-4 py-2 text-2xs text-faint">{price.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>

      <p className="text-2xs text-faint">
        Every figure on this page is computed by the backend from the seeded demo database. Weather
        provider: {f.weather_source === "OPEN_METEO" ? "Open-Meteo (auto)" : "deterministic mock provider"}.
        Each weather sample and optimization run records the source it actually used.
      </p>
    </div>
  );
}
