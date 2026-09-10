"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge, StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Empty, ErrorNote } from "@/components/ui/feedback";
import { api } from "@/lib/api";
import { num, utcShort } from "@/lib/format";
import type { Recommendation } from "@/types";

export function RecommendationRail({ items }: { items: Recommendation[] }) {
  const [rows, setRows] = useState(items);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);

  async function decide(rec: Recommendation, kind: "approve" | "reject") {
    setBusy(rec.id);
    setError(null);
    try {
      const updated =
        kind === "approve" ? await api.approve(rec.id) : await api.reject(rec.id);
      setRows((r) => r.map((x) => (x.id === rec.id ? updated : x)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "That decision could not be recorded");
    } finally {
      setBusy(null);
    }
  }

  if (rows.length === 0) {
    return <Empty>No pending recommendations. Optimize a voyage to create one.</Empty>;
  }

  return (
    <div className="divide-y divide-hairline">
      {error ? <ErrorNote message={error} className="m-3" /> : null}
      {rows.map((rec) => (
        <article key={rec.id} className="p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <Link
                href={`/voyage?id=${rec.voyage_id}`}
                className="text-sm text-ink hover:text-brass"
              >
                {rec.vessel_name}
              </Link>
              <p className="mt-0.5 font-mono tnum text-2xs text-faint">{rec.voyage_reference}</p>
            </div>
            {rec.status === "PENDING" ? (
              <Badge tone="brass">{rec.route_label}</Badge>
            ) : (
              <StatusBadge status={rec.status} />
            )}
          </div>

          <dl className="mt-3 grid grid-cols-3 gap-2">
            <div>
              <dt className="label">Fuel saving</dt>
              <dd className="mt-0.5 font-mono tnum text-sm text-kelp">
                {num(rec.fuel_saving_mt, 1)} MT
              </dd>
            </div>
            <div>
              <dt className="label">CO2 saving</dt>
              <dd className="mt-0.5 font-mono tnum text-sm text-ink">
                {num(rec.co2_saving_mt, 1)} MT
              </dd>
            </div>
            <div>
              <dt className="label">ETA</dt>
              <dd className="mt-0.5 font-mono tnum text-sm text-ink">
                {utcShort(rec.option?.eta_utc)}
              </dd>
            </div>
          </dl>

          <p className="mt-3 line-clamp-3 text-xs leading-relaxed text-dim">{rec.rationale}</p>

          {rec.status === "PENDING" ? (
            <div className="mt-3 flex gap-2">
              <Button
                size="sm"
                variant="approve"
                disabled={busy === rec.id}
                onClick={() => decide(rec, "approve")}
              >
                Approve
              </Button>
              <Button
                size="sm"
                variant="danger"
                disabled={busy === rec.id}
                onClick={() => decide(rec, "reject")}
              >
                Reject
              </Button>
              <Link href={`/voyage?id=${rec.voyage_id}`} className="ml-auto">
                <Button size="sm" variant="ghost">
                  Open voyage
                </Button>
              </Link>
            </div>
          ) : (
            <p className="mt-3 text-2xs text-kelp">
              Recommendation {rec.status.toLowerCase()}.
            </p>
          )}
        </article>
      ))}
    </div>
  );
}
