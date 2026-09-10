"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { num } from "@/lib/format";
import { token } from "@/lib/theme";

/** Recharts takes colour strings, so the palette is read once per theme. */
function usePalette() {
  const [palette, setPalette] = useState({
    axis: "#2A4055",
    tick: "#5A7188",
    grid: "#162634",
    sea: "#4C9BC4",
    brass: "#E3A54B",
    kelp: "#4FB286",
    deepSea: "#2F6A88",
  });

  useEffect(() => {
    const read = () =>
      setPalette({
        axis: token("hairline"),
        tick: token("faint"),
        grid: token("hairline", 0.55),
        sea: token("sea"),
        brass: token("brass"),
        kelp: token("kelp"),
        deepSea: token("sea", 0.65),
      });
    read();
    window.addEventListener("nav-theme", read);
    return () => window.removeEventListener("nav-theme", read);
  }, []);

  return palette;
}

function TooltipBox({ active, payload, label, unit }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="border border-hairline bg-hull px-3 py-2 text-xs">
      <div className="text-dim">{label}</div>
      {payload.map((entry: any) => (
        <div key={entry.dataKey} className="mt-1 flex items-center gap-2">
          <span className="h-2 w-2" style={{ background: entry.color }} />
          <span className="text-faint">{entry.name}</span>
          <span className="ml-auto font-mono tnum text-ink">
            {num(entry.value, 1)} {unit}
          </span>
        </div>
      ))}
    </div>
  );
}

export function PredictedVsActualChart({
  data,
}: {
  data: Array<{ label: string; predicted: number; actual: number }>;
}) {
  const c = usePalette();
  const AXIS = { stroke: c.axis, tick: { fill: c.tick, fontSize: 11 } };
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: -12 }}>
        <CartesianGrid stroke={c.grid} vertical={false} />
        <XAxis dataKey="label" {...AXIS} tickLine={false} />
        <YAxis {...AXIS} tickLine={false} width={56} />
        <Tooltip content={<TooltipBox unit="MT" />} cursor={{ stroke: c.axis }} />
        <Legend
          wrapperStyle={{ fontSize: 11, color: c.tick }}
          iconType="plainline"
          iconSize={14}
        />
        <Line
          type="monotone"
          dataKey="predicted"
          name="Predicted fuel"
          stroke={c.sea}
          strokeWidth={1.6}
          strokeDasharray="4 3"
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="actual"
          name="Actual fuel"
          stroke={c.brass}
          strokeWidth={1.8}
          dot={{ r: 2, fill: c.brass, strokeWidth: 0 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function FuelByVesselChart({
  data,
}: {
  data: Array<{ vessel: string; planned_fuel_mt: number; consumed_fuel_mt: number }>;
}) {
  const c = usePalette();
  const AXIS = { stroke: c.axis, tick: { fill: c.tick, fontSize: 11 } };
  return (
    <ResponsiveContainer width="100%" height={Math.max(240, data.length * 34)}>
      <BarChart data={data} layout="vertical" margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
        <CartesianGrid stroke={c.grid} horizontal={false} />
        <XAxis type="number" {...AXIS} tickLine={false} />
        <YAxis type="category" dataKey="vessel" {...AXIS} tickLine={false} width={128} />
        <Tooltip content={<TooltipBox unit="MT" />} cursor={{ fill: token("sea", 0.08) }} />
        <Legend wrapperStyle={{ fontSize: 11, color: c.tick }} iconType="square" iconSize={9} />
        <Bar dataKey="planned_fuel_mt" name="Planned" fill={c.deepSea} barSize={9} />
        <Bar dataKey="consumed_fuel_mt" name="Consumed" fill={c.brass} barSize={9} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function EmissionsChart({
  data,
}: {
  data: Array<{ month: string; co2_mt: number }>;
}) {
  const c = usePalette();
  const AXIS = { stroke: c.axis, tick: { fill: c.tick, fontSize: 11 } };
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: -12 }}>
        <CartesianGrid stroke={c.grid} vertical={false} />
        <XAxis dataKey="month" {...AXIS} tickLine={false} />
        <YAxis {...AXIS} tickLine={false} width={64} />
        <Tooltip content={<TooltipBox unit="MT" />} cursor={{ fill: token("sea", 0.08) }} />
        <Bar dataKey="co2_mt" name="CO2" barSize={22}>
          {data.map((entry) => (
            <Cell key={entry.month} fill={c.kelp} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
