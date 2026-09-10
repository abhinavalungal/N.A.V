import * as React from "react";

import { cn } from "@/lib/utils";

export function Panel({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <section className={cn("panel", className)} {...props} />;
}

export function PanelHeader({
  title,
  caption,
  actions,
  className,
}: {
  title: React.ReactNode;
  caption?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <header className={cn("panel-header", className)}>
      <div className="min-w-0">
        <h2 className="truncate text-sm font-medium text-ink">{title}</h2>
        {caption ? <p className="mt-0.5 truncate text-xs text-faint">{caption}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </header>
  );
}

export function Field({
  label,
  value,
  mono = true,
  className,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
  className?: string;
}) {
  return (
    <div className={cn("min-w-0", className)}>
      <div className="label">{label}</div>
      <div className={cn("mt-1 truncate text-sm text-ink", mono && "font-mono tnum")}>
        {value}
      </div>
    </div>
  );
}
