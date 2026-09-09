"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

/**
 * Re-runs the server-side probes. Nothing polls on a timer: a stale reading
 * that refreshes itself is harder to trust than one the operator asked for.
 */
export function RefreshButton() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [checkedAt, setCheckedAt] = useState<string | null>(null);

  function refresh() {
    startTransition(() => {
      router.refresh();
      setCheckedAt(new Date().toLocaleTimeString());
    });
  }

  return (
    <div className="flex items-center gap-3">
      {checkedAt ? (
        <span className="tabular font-mono text-micro text-muted">
          checked {checkedAt}
        </span>
      ) : null}
      <button
        type="button"
        onClick={refresh}
        disabled={isPending}
        className="rounded-panel border border-primary/50 bg-primary/10 px-3 py-1 text-xs font-medium text-primary transition-colors hover:bg-primary/20 disabled:opacity-50"
      >
        {isPending ? "Checking…" : "Check again"}
      </button>
    </div>
  );
}
