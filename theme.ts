"use client";

import { useEffect, useState } from "react";

export type Theme = "dark" | "light";

export const THEME_STORAGE_KEY = "nav-theme";

/** Read a palette variable as a CSS colour. MapLibre and Recharts need real
 *  colour strings, not Tailwind class names. */
export function token(name: string, alpha = 1): string {
  if (typeof window === "undefined") return "#000000";
  const channels = getComputedStyle(document.documentElement)
    .getPropertyValue(`--${name}`)
    .trim();
  if (!channels) return "#000000";
  return alpha === 1 ? `rgb(${channels})` : `rgb(${channels} / ${alpha})`;
}

export function currentTheme(): Theme {
  if (typeof document === "undefined") return "dark";
  return document.documentElement.dataset.theme === "light" ? "light" : "dark";
}

export function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Private browsing, or storage disabled. The theme still applies.
  }
  // Components that paint their own colours (the chart, the graphs) listen
  // for this rather than re-reading on every render.
  window.dispatchEvent(new CustomEvent("nav-theme", { detail: theme }));
}

/** Current theme, re-rendering the caller whenever it changes. */
export function useTheme(): [Theme, (next: Theme) => void] {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    setTheme(currentTheme());
    const onChange = (event: Event) => setTheme((event as CustomEvent).detail as Theme);
    window.addEventListener("nav-theme", onChange);
    return () => window.removeEventListener("nav-theme", onChange);
  }, []);

  return [theme, applyTheme];
}

/** Route variant colours, resolved for the theme in force. */
export function routeColor(code: string): string {
  const map: Record<string, string> = {
    FASTEST: "route-fastest",
    FUEL_EFFICIENT: "route-fuel",
    WEATHER_OPTIMIZED: "route-weather",
    ECO_SLOW_STEAM: "route-eco",
  };
  return token(map[code] ?? "sea");
}
