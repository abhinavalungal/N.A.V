import * as React from "react";

import { cn } from "@/lib/utils";

const tones: Record<string, string> = {
  neutral: "border-hairline bg-deck text-dim",
  active: "border-[#1f4a5f] bg-[#0f2733] text-sea",
  planned: "border-hairline bg-deck text-dim",
  completed: "border-[#26543f] bg-[#12291f] text-kelp",
  brass: "border-[#5a4423] bg-[#221a0e] text-brass",
  alert: "border-[#4a2723] bg-[#2a1614] text-coral",
  good: "border-[#26543f] bg-[#12291f] text-kelp",
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
