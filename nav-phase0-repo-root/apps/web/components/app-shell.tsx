import Link from "next/link";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";

/**
 * Persistent left rail. Every destination in the product plan is listed so the
 * shape of N.A.V. is visible from day one, but only what exists is clickable -
 * the rest carry the phase that will build them.
 */
const NAVIGATION: { label: string; href?: string; phase?: string }[] = [
  { label: "System status", href: "/" },
  { label: "Dashboard", phase: "7" },
  { label: "Fleet", phase: "2" },
  { label: "Vessels", phase: "2" },
  { label: "Voyages", phase: "2" },
  { label: "Optimisation", phase: "4" },
  { label: "Weather", phase: "3" },
  { label: "Fuel", phase: "3" },
  { label: "Emissions", phase: "3" },
  { label: "Recommendations", phase: "6" },
  { label: "Approvals", phase: "6" },
  { label: "Messages", phase: "6" },
  { label: "Agent activity", phase: "5" },
  { label: "Analytics", phase: "8" },
  { label: "Documents", phase: "9" },
  { label: "Settings", phase: "1" },
];

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      <nav
        aria-label="Primary"
        className="border-b bg-surface lg:w-60 lg:shrink-0 lg:border-b-0 lg:border-r"
      >
        <div className="flex items-baseline gap-2 px-4 py-4">
          <span className="font-mono text-base font-medium tracking-[0.2em] text-primary">
            N.A.V.
          </span>
          <span className="text-micro text-muted">Nautical Agentic Navigator</span>
        </div>

        <ul className="flex gap-1 overflow-x-auto px-2 pb-3 lg:block lg:overflow-visible lg:pb-6">
          {NAVIGATION.map((item) =>
            item.href ? (
              <li key={item.label}>
                <Link
                  href={item.href}
                  className="block whitespace-nowrap rounded-panel bg-raised px-3 py-1.5 text-sm text-ink"
                >
                  {item.label}
                </Link>
              </li>
            ) : (
              <li
                key={item.label}
                title={`Not built yet - scheduled for Phase ${item.phase}`}
                className="flex items-center justify-between gap-3 whitespace-nowrap px-3 py-1.5 text-sm text-muted"
              >
                {item.label}
                <span className="font-mono text-micro text-muted/70">
                  P{item.phase}
                  <span className="sr-only"> - not built yet</span>
                </span>
              </li>
            ),
          )}
        </ul>
      </nav>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b px-6 py-3">
          <p className="text-sm text-muted">Intelligence for Every Voyage.</p>
          <Badge tone="signal">Phase 0 · foundation only</Badge>
        </header>
        <main className="flex-1 px-6 py-6">{children}</main>
      </div>
    </div>
  );
}
