import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge conditional class names, letting later Tailwind classes win. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Render a probe latency, or an em dash when there is nothing to render. */
export function formatLatency(ms: number | null): string {
  return ms === null ? "—" : `${ms.toFixed(1)} ms`;
}
