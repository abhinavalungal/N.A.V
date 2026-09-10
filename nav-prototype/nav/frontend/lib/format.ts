const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

function parseUtc(value: string): Date {
  // Backend timestamps are naive UTC.
  return new Date(value.endsWith("Z") ? value : `${value}Z`);
}

export function utcDateTime(value?: string | null): string {
  if (!value) return "—";
  const d = parseUtc(value);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getUTCDate())} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()} ${pad(
    d.getUTCHours(),
  )}:${pad(d.getUTCMinutes())} UTC`;
}

export function utcShort(value?: string | null): string {
  if (!value) return "—";
  const d = parseUtc(value);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getUTCDate())} ${MONTHS[d.getUTCMonth()]} ${pad(d.getUTCHours())}:${pad(
    d.getUTCMinutes(),
  )}`;
}

export function num(value?: number | null, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toLocaleString("en-GB", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function signed(value: number, digits = 1, unit = ""): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${num(value, digits)}${unit}`;
}

export function hours(value?: number | null): string {
  if (value === null || value === undefined) return "—";
  const d = Math.floor(value / 24);
  const h = Math.round(value % 24);
  return d > 0 ? `${d}d ${h}h` : `${h}h`;
}

export function coord(lat?: number | null, lon?: number | null): string {
  if (lat === null || lat === undefined || lon === null || lon === undefined) return "—";
  const ns = lat >= 0 ? "N" : "S";
  const ew = lon >= 0 ? "E" : "W";
  return `${Math.abs(lat).toFixed(2)}° ${ns}  ${Math.abs(lon).toFixed(2)}° ${ew}`;
}

export function riskLabel(band?: string | null): string {
  if (!band) return "—";
  return band.charAt(0) + band.slice(1).toLowerCase().replace(/_/g, " ");
}

export const OBJECTIVE_LABELS: Record<string, string> = {
  MIN_FUEL: "Minimum fuel",
  FASTEST: "Fastest arrival",
  MIN_EMISSIONS: "Minimum emissions",
  BALANCED: "Balanced",
};
