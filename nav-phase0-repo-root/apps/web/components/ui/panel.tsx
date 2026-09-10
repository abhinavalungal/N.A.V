import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

export function Panel({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <section className={cn("rounded-panel border bg-surface", className)} {...props} />;
}

export function PanelHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <header className="flex items-start justify-between gap-4 border-b px-4 py-3">
      <div>
        <h2 className="text-sm font-semibold tracking-tight">{title}</h2>
        {description ? (
          <p className="mt-0.5 max-w-prose text-xs text-muted">{description}</p>
        ) : null}
      </div>
      {action}
    </header>
  );
}
