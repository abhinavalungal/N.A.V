"use client";

import maplibregl, { LngLatBounds, Map as MapLibreMap, Marker } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef } from "react";

import { token } from "@/lib/theme";

export interface MapRoute {
  id: string;
  coordinates: number[][]; // [lon, lat]
  color: string;
  width?: number;
  dashed?: boolean;
  opacity?: number;
}

export interface MapMarker {
  id: string;
  lon: number;
  lat: number;
  kind: "vessel" | "origin" | "destination" | "waypoint";
  label?: string;
  detail?: string;
  heading?: number;
  muted?: boolean;
  onClick?: () => void;
}

interface Props {
  routes?: MapRoute[];
  markers?: MapMarker[];
  fitTo?: number[][];
  className?: string;
  zoom?: number;
  center?: [number, number];
}


/** Meridians and parallels, drawn like a chart graticule. */
function graticule(): GeoJSON.FeatureCollection {
  const features: GeoJSON.Feature[] = [];
  for (let lon = -180; lon <= 180; lon += 20) {
    features.push({
      type: "Feature",
      properties: {},
      geometry: {
        type: "LineString",
        coordinates: Array.from({ length: 37 }, (_, i) => [lon, -90 + i * 5]),
      },
    });
  }
  for (let lat = -80; lat <= 80; lat += 20) {
    features.push({
      type: "Feature",
      properties: {},
      geometry: {
        type: "LineString",
        coordinates: Array.from({ length: 73 }, (_, i) => [-180 + i * 5, lat]),
      },
    });
  }
  return { type: "FeatureCollection", features };
}

/** Keep longitudes continuous so Pacific routes don't wrap across the map. */
function unwrap(coords: number[][]): number[][] {
  if (coords.length === 0) return coords;
  const out: number[][] = [[...coords[0]]];
  let offset = 0;
  for (let i = 1; i < coords.length; i += 1) {
    const prev = coords[i - 1][0] + offset;
    let lon = coords[i][0] + offset;
    if (lon - prev > 180) offset -= 360;
    if (lon - prev < -180) offset += 360;
    lon = coords[i][0] + offset;
    out.push([lon, coords[i][1]]);
  }
  return out;
}

function styleSpec(): maplibregl.StyleSpecification | string {
  const external = process.env.NEXT_PUBLIC_MAP_STYLE_URL;
  if (external) return external;
  // Colours are read from the palette in force, so the chart follows the
  // theme instead of staying dark on a light page.
  return {
    version: 8,
    sources: {
      land: {
        type: "geojson",
        data: "/data/land.geojson",
        attribution: "Land: Natural Earth (public domain)",
      },
      graticule: { type: "geojson", data: graticule() as never },
    },
    layers: [
      { id: "sea", type: "background", paint: { "background-color": token("chart-sea") } },
      {
        id: "graticule",
        type: "line",
        source: "graticule",
        paint: { "line-color": token("chart-grid"), "line-width": 0.6 },
      },
      { id: "land", type: "fill", source: "land", paint: { "fill-color": token("chart-land") } },
      {
        id: "coastline",
        type: "line",
        source: "land",
        paint: { "line-color": token("chart-coast"), "line-width": 0.7 },
      },
    ],
  };
}

function markerElement(marker: MapMarker): HTMLElement {
  const el = document.createElement("div");
  el.className = "nav-marker";
  el.style.cursor = marker.onClick ? "pointer" : "default";
  if (marker.kind === "vessel") {
    el.innerHTML = `
      <svg width="22" height="22" viewBox="0 0 22 22" style="transform: rotate(${marker.heading ?? 0}deg); overflow: visible;">
        <circle cx="11" cy="11" r="9.5" fill="${token("brass", 0.14)}" stroke="${token("brass", 0.45)}" />
        <path d="M11 3 L15.5 17 L11 14 L6.5 17 Z" fill="${marker.muted ? token("dim") : token("brass")}" />
      </svg>`;
  } else if (marker.kind === "waypoint") {
    el.innerHTML = `<svg width="8" height="8" viewBox="0 0 8 8"><circle cx="4" cy="4" r="2.5" fill="${token("sea")}" opacity="0.8"/></svg>`;
  } else {
    const color = marker.kind === "origin" ? token("dim") : token("kelp");
    el.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 14 14">
        <rect x="3" y="3" width="8" height="8" fill="none" stroke="${color}" stroke-width="1.6" />
        <rect x="6" y="6" width="2" height="2" fill="${color}" />
      </svg>`;
  }
  return el;
}

export default function MapView({
  routes = [],
  markers = [],
  fitTo,
  className,
  zoom = 1.4,
  center = [40, 20],
}: Props) {
  const container = useRef<HTMLDivElement | null>(null);
  const map = useRef<MapLibreMap | null>(null);
  const drawn = useRef<string[]>([]);
  const pins = useRef<Marker[]>([]);
  const ready = useRef(false);

  useEffect(() => {
    if (!container.current || map.current) return;
    const instance = new maplibregl.Map({
      container: container.current,
      style: styleSpec(),
      center,
      zoom,
      minZoom: 0.6,
      maxZoom: 9,
      attributionControl: { compact: true },
      dragRotate: false,
      renderWorldCopies: true,
    });
    instance.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    instance.on("load", () => {
      ready.current = true;
      instance.resize();
      draw();
    });
    map.current = instance;
    return () => {
      instance.remove();
      map.current = null;
      ready.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function draw() {
    const instance = map.current;
    if (!instance || !ready.current) return;

    drawn.current.forEach((id) => {
      if (instance.getLayer(id)) instance.removeLayer(id);
      if (instance.getSource(id)) instance.removeSource(id);
    });
    drawn.current = [];
    pins.current.forEach((m) => m.remove());
    pins.current = [];

    routes.forEach((route) => {
      if (route.coordinates.length < 2) return;
      const id = `route-${route.id}`;
      instance.addSource(id, {
        type: "geojson",
        data: {
          type: "Feature",
          properties: {},
          geometry: { type: "LineString", coordinates: unwrap(route.coordinates) },
        },
      });
      instance.addLayer({
        id,
        type: "line",
        source: id,
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": route.color,
          "line-width": route.width ?? 2,
          "line-opacity": route.opacity ?? 1,
          ...(route.dashed ? { "line-dasharray": [2, 2] } : {}),
        },
      });
      drawn.current.push(id);
    });

    markers.forEach((marker) => {
      const el = markerElement(marker);
      const pin = new maplibregl.Marker({ element: el }).setLngLat([marker.lon, marker.lat]);
      if (marker.label) {
        pin.setPopup(
          new maplibregl.Popup({ offset: 14, closeButton: false }).setHTML(
            `<div style="font-weight:500">${marker.label}</div>${
              marker.detail ? `<div style="color:${token("dim")};margin-top:2px">${marker.detail}</div>` : ""
            }`,
          ),
        );
      }
      if (marker.onClick) el.addEventListener("click", marker.onClick);
      pin.addTo(instance);
      pins.current.push(pin);
    });

    const fitPoints = fitTo ?? routes.flatMap((r) => unwrap(r.coordinates));
    if (fitPoints && fitPoints.length > 1) {
      const bounds = fitPoints.reduce(
        (acc, c) => acc.extend(c as [number, number]),
        new LngLatBounds(fitPoints[0] as [number, number], fitPoints[0] as [number, number]),
      );
      instance.fitBounds(bounds, { padding: 56, duration: 0, maxZoom: 6 });
    }
  }

  useEffect(() => {
    draw();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(routes), JSON.stringify(markers), JSON.stringify(fitTo)]);

  // The basemap colours are baked into the style, so a theme change means a
  // new style. Routes and markers are redrawn once it has loaded.
  useEffect(() => {
    const onTheme = () => {
      const instance = map.current;
      if (!instance) return;
      ready.current = false;
      instance.setStyle(styleSpec());
      instance.once("styledata", () => {
        ready.current = true;
        drawn.current = [];
        draw();
      });
    };
    window.addEventListener("nav-theme", onTheme);
    return () => window.removeEventListener("nav-theme", onTheme);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Callers change the centre to focus a vessel; the map is only built once.
  useEffect(() => {
    const instance = map.current;
    if (!instance || !ready.current || fitTo || routes.length > 0) return;
    instance.easeTo({ center, zoom, duration: 400 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [center[0], center[1], zoom]);

  return <div ref={container} className={className} />;
}
