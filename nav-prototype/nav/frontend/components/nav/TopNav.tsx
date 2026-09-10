"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Meta } from "@/types";

const LINKS = [
  { href: "/", label: "Dashboard", section: ["/"] },
  { href: "/fleet", label: "Fleet", section: ["/fleet"] },
  // The detail pages are /vessel?id= and /voyage?id=, so each tab owns both
  // its list route and its singular detail route.
  { href: "/vessels", label: "Vessels", section: ["/vessels", "/vessel"] },
  { href: "/voyages", label: "Voyages", section: ["/voyages", "/voyage"] },
  { href: "/optimization", label: "Optimization", section: ["/optimization"] },
  { href: "/analytics", label: "Analytics", section: ["/analytics"] },
];

export function TopNav() {
  const pathname = usePathname();
  const [meta, setMeta] = useState<Meta | null>(null);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    api
      .meta()
      .then(setMeta)
      .catch(() => setOffline(true));
  }, []);

  return (
    <header className="sticky top-0 z-30 border-b border-hairline bg-abyss/95 backdrop-blur">
      <div className="mx-auto flex h-14 w-full max-w-[1760px] items-center gap-6 px-5">
        <Link href="/" className="flex items-baseline gap-2.5">
          <span className="font-mono text-lg font-medium tracking-[0.18em] text-ink">N.A.V.</span>
          <span className="hidden text-xs text-faint lg:inline">Nautical Agentic Navigator</span>
        </Link>

        <nav className="flex items-center gap-0.5">
          {LINKS.map((link) => {
            const path = pathname.replace(/\/$/, "") || "/";
            const active =
              link.href === "/"
                ? path === "/"
                : link.section.some((base) => path === base || path.startsWith(`${base}/`));
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "relative px-3 py-4 text-xs transition-colors",
                  active ? "text-ink" : "text-dim hover:text-ink",
                )}
              >
                {link.label}
                {active ? (
                  <span className="absolute inset-x-2 -bottom-px h-px bg-brass" />
                ) : null}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-4 text-2xs text-faint">
          {offline ? (
            <span className="text-coral">Backend offline</span>
          ) : meta ? (
            <>
              <span className="hidden md:inline">
                Agent{" "}
                <span className="font-mono text-dim">
                  {meta.ai_provider === "openai" ? meta.ai_model : "mock mode"}
                </span>
              </span>
              <span
                className="hidden md:inline"
                title="Configured provider. Individual samples show the source they actually came from; Open-Meteo falls back to the deterministic mock provider when it is unreachable."
              >
                Weather{" "}
                <span
                  className={cn(
                    "font-mono",
                    meta.weather_provider === "OPEN_METEO" ? "text-kelp" : "text-brass",
                  )}
                >
                  {meta.weather_provider === "OPEN_METEO" ? "Open-Meteo (auto)" : "mock"}
                </span>
              </span>
              <span className="font-mono">v{meta.version}</span>
            </>
          ) : null}
        </div>
      </div>
    </header>
  );
}
