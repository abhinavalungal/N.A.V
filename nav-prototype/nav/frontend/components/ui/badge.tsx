import * as React from "react";

import { cn } from "@/lib/utils";

const tones: Record<string, string> = {
  neutral: "border-hairline bg-deck text-dim",
  active: "border-sea/35 bg-sea/10 text-sea",
  planned: "border-hairline bg-deck text-dim",
  completed: "border-kelp/35 bg-kelp/10 text-kelp",
  brass: "border-brass/40 bg-brass/10 text-brass",
  alert: "border-coral/35 bg-coral/10 text-coral",
  good: "border-kelp/35 bg-kelp/10 text-kelp",
};

export function Badge({
  tone = "neutral",
  className,
  children,
}: {
  tone?: keyof typeof tones | string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 whitespace-nowrap rounded-sm border px-1.5 py-0.5 text-2xs",
        tones[tone] ?? tones.neutral,
        className,
      )}
    >
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const tone =
    status === "ACTIVE"
      ? "active"
      : status === "COMPLETED"
        ? "completed"
        : status === "APPROVED"
          ? "good"
          : status === "REJECTED"
            ? "alert"
            : status === "MODIFIED"
              ? "brass"
              : "planned";
  return <Badge tone={tone}>{status}</Badge>;
}

export function RiskBadge({ band }: { band: string }) {
  const tone =
    band === "VERY_LOW" || band === "LOW"
      ? "good"
      : band === "MODERATE"
        ? "brass"
        : "alert";
  return <Badge tone={tone}>{band.replace("_", " ").toLowerCase()}</Badge>;
}
