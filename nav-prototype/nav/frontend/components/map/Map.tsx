"use client";

import dynamic from "next/dynamic";

import type { MapMarker, MapRoute } from "./MapView";

/** MapLibre touches window, so it only ever loads in the browser. */
export const Map = dynamic(() => import("./MapView"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-hull text-xs text-faint">
      Loading chart…
    </div>
  ),
});

export type { MapMarker, MapRoute };
