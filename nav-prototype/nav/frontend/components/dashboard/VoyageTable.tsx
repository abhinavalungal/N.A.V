"use client";

import Link from "next/link";
import { AlertTriangle, Info } from "lucide-react";

import { StatusBadge } from "@/components/ui/badge";
import { Empty } from "@/components/ui/feedback";
import { num, utcShort } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Voyage, VoyageAlert } from "@/types";

export function VoyageTable({
  voyages,
  alerts = [],
  showStatus = true,
}: {
  voyages: Voyage[];
  alerts?: VoyageAlert[];
  showStatus?: boolean;
}) {
  if (voyages.length === 0) {
    return <Empty>No voyages match this view. Create one from the Voyages page.</Empty>;
  }

  const byVoyage = new Map<number, VoyageAlert>();
  const rank = { ACTION: 0, WATCH: 1, INFO: 2 };
  alerts.forEach((alert) => {
    const current = byVoyage.get(alert.voyage_id);
    if (!current || rank[alert.severity] < rank[current.severity]) {
      byVoyage.set(alert.voyage_id, alert);
    }
  });

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[880px] border-collapse text-xs">
        <thead>
          <tr className="border-b border-hairline text-left text-2xs text-faint">
            <th className="px-4 py-2.5 font-normal">Vessel</th>
            <th className="px-4 py-2.5 font-normal">Voyage</th>
            <th className="px-4 py-2.5 font-normal">Route</th>
            <th className="px-4 py-2.5 text-right font-normal">Progress</th>
            <th className="px-4 py-2.5 text-right font-normal">ETA (UTC)</th>
            <th className="px-4 py-2.5 text-right font-normal">Fuel plan</th>
            {showStatus ? <th className="px-4 py-2.5 font-normal">Status</th> : null}
            <th className="px-4 py-2.5 font-normal">N.A.V. alert</th>
          </tr>
        </thead>
        <tbody>
          {voyages.map((voyage) => {
            const alert = byVoyage.get(voyage.id);
            const progress =
              voyage.distance_nm > 0
                ? Math.max(
                    0,
                    Math.min(
                      100,
                      ((voyage.distance_nm - voyage.distance_remaining_nm) / voyage.distance_nm) *
                        100,
                    ),
                  )
                : 0;
            return (
              <tr
                key={voyage.id}
                className="border-b border-hairline/60 transition-colors last:border-0 hover:bg-deck"
              >
                <td className="px-4 py-2.5">
                  <Link href={`/vessel?id=${voyage.vessel_id}`} className="text-ink hover:text-brass">
                    {voyage.vessel_name}
                  </Link>
                </td>
                <td className="px-4 py-2.5">
                  <Link
                    href={`/voyage?id=${voyage.id}`}
                    className="font-mono tnum text-dim hover:text-brass"
                  >
                    {voyage.reference}
                  </Link>
                </td>
                <td className="px-4 py-2.5 text-dim">
                  {voyage.origin_port} <span className="text-faint">to</span>{" "}
                  {voyage.destination_port}
                </td>
                <td className="px-4 py-2.5">
                  <div className="flex items-center justify-end gap-2">
                    <div className="h-1 w-16 bg-deck">
                      <div className="h-full bg-sea" style={{ width: `${progress}%` }} />
                    </div>
                    <span className="w-9 text-right font-mono tnum text-dim">
                      {progress.toFixed(0)}%
                    </span>
                  </div>
                </td>
                <td className="px-4 py-2.5 text-right font-mono tnum text-dim">
                  {utcShort(voyage.expected_arrival_utc)}
                </td>
                <td className="px-4 py-2.5 text-right font-mono tnum text-dim">
                  {num(voyage.planned_fuel_mt, 1)} MT
                </td>
                {showStatus ? (
                  <td className="px-4 py-2.5">
                    <StatusBadge status={voyage.status} />
                  </td>
                ) : null}
                <td className="max-w-[280px] px-4 py-2.5">
                  {alert ? (
                    <span
                      className={cn(
                        "flex items-start gap-1.5",
                        alert.severity === "ACTION"
                          ? "text-coral"
                          : alert.severity === "WATCH"
                            ? "text-brass"
                            : "text-dim",
                      )}
                    >
                      {alert.severity === "INFO" ? (
                        <Info className="mt-0.5 h-3 w-3 shrink-0" />
                      ) : (
                        <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
                      )}
                      {alert.message}
                    </span>
                  ) : (
                    <span className="text-faint">—</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
