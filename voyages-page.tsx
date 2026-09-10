"use client";

import Link from "next/link";
import { useState } from "react";

import { VoyageTable } from "@/components/dashboard/VoyageTable";
import { Button } from "@/components/ui/button";
import { Panel, PanelHeader } from "@/components/ui/card";
import { ErrorNote, Loading } from "@/components/ui/feedback";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const FILTERS = ["ALL", "ACTIVE", "PLANNED", "COMPLETED"] as const;

export default function VoyagesPage() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("ALL");
  const voyages = useApi(() => api.voyages(filter === "ALL" ? undefined : filter), [filter]);
  const alerts = useApi(() => api.alerts());

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-medium">Voyages</h1>
          <p className="mt-1 text-xs text-dim">
            Open a voyage to see its passage plan, the weather along the track and what
            N.A.V. suggests.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/optimization">
            <Button variant="secondary">Compare route options</Button>
          </Link>
          <Link href="/voyages/new">
            <Button variant="primary">Plan a voyage</Button>
          </Link>
        </div>
      </div>

      <Panel>
        <PanelHeader
          title="Voyage register"
          caption={`${voyages.data?.length ?? 0} voyages`}
          actions={
            <div className="flex gap-1">
              {FILTERS.map((option) => (
                <button
                  key={option}
                  onClick={() => setFilter(option)}
                  className={cn(
                    "border px-2.5 py-1 text-2xs transition-colors",
                    filter === option
                      ? "border-brass/50 bg-brass/10 text-brass"
                      : "border-hairline bg-deck text-dim hover:text-ink",
                  )}
                >
                  {option === "ALL" ? "All" : option.charAt(0) + option.slice(1).toLowerCase()}
                </button>
              ))}
            </div>
          }
        />
        {voyages.loading ? <Loading /> : null}
        {voyages.error ? <ErrorNote message={voyages.error} className="m-4" /> : null}
        {voyages.data ? <VoyageTable voyages={voyages.data} alerts={alerts.data ?? []} /> : null}
      </Panel>
    </div>
  );
}
