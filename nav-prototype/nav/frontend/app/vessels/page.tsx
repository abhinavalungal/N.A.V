"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Panel, PanelHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/controls";
import { Empty, ErrorNote, Loading } from "@/components/ui/feedback";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { coord, num } from "@/lib/format";

export default function VesselsPage() {
  const [search, setSearch] = useState("");
  const vessels = useApi(() => api.vessels(), []);
  const rows = (vessels.data ?? []).filter((v) =>
    `${v.name} ${v.imo} ${v.vessel_type}`.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-medium">Vessels</h1>
        <p className="mt-1 text-xs text-dim">
          Ten demo vessels with particulars used by the fuel, ETA and emissions models.
        </p>
      </div>

      <Panel>
        <PanelHeader
          title="Fleet register"
          caption={`${rows.length} vessels`}
          actions={
            <Input
              placeholder="Search name, IMO or type"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-8 w-64 font-sans text-xs"
            />
          }
        />
        {vessels.loading ? <Loading /> : null}
        {vessels.error ? <ErrorNote message={vessels.error} className="m-4" /> : null}
        {vessels.data && rows.length === 0 ? <Empty>No vessel matches that search.</Empty> : null}
        {rows.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] border-collapse text-xs">
              <thead>
                <tr className="border-b border-hairline text-left text-2xs text-faint">
                  <th className="px-4 py-2.5 font-normal">Name</th>
                  <th className="px-4 py-2.5 font-normal">IMO</th>
                  <th className="px-4 py-2.5 font-normal">Type</th>
                  <th className="px-4 py-2.5 text-right font-normal">DWT</th>
                  <th className="px-4 py-2.5 text-right font-normal">Design speed</th>
                  <th className="px-4 py-2.5 text-right font-normal">Current speed</th>
                  <th className="px-4 py-2.5 font-normal">Fuel</th>
                  <th className="px-4 py-2.5 font-normal">Position</th>
                  <th className="px-4 py-2.5 font-normal">Status</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((vessel) => (
                  <tr
                    key={vessel.id}
                    className="border-b border-hairline/60 transition-colors last:border-0 hover:bg-deck"
                  >
                    <td className="px-4 py-2.5">
                      <Link href={`/vessel?id=${vessel.id}`} className="text-ink hover:text-brass">
                        {vessel.name}
                      </Link>
                    </td>
                    <td className="px-4 py-2.5 font-mono tnum text-dim">{vessel.imo}</td>
                    <td className="px-4 py-2.5 text-dim">{vessel.vessel_type}</td>
                    <td className="px-4 py-2.5 text-right font-mono tnum text-dim">
                      {num(vessel.deadweight_t)}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono tnum text-dim">
                      {num(vessel.design_speed_kn, 1)} kn
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono tnum text-dim">
                      {num(vessel.current_speed_kn, 1)} kn
                    </td>
                    <td className="px-4 py-2.5 text-dim">{vessel.fuel_type}</td>
                    <td className="px-4 py-2.5 font-mono tnum text-faint">
                      {coord(vessel.latitude, vessel.longitude)}
                    </td>
                    <td className="px-4 py-2.5">
                      <Badge tone={vessel.status === "AT_SEA" ? "active" : "neutral"}>
                        {vessel.status}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </Panel>
    </div>
  );
}
