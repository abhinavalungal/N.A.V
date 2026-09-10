import { AlertTriangle, Loader2 } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

export function Loading({ label = "Loading", className }: { label?: string; className?: string }) {
  return (
    <div className={cn("flex items-center gap-2 px-4 py-6 text-xs text-faint", className)}>
      <Loader2 className="h-3.5 w-3.5 animate-spin" />
      {label}
    </div>
  );
}

export function ErrorNote({ message, className }: { message: string; className?: string }) {
  return (
    <div
      className={cn(
        "flex items-start gap-2 border border-[#4a2723] bg-[#1c0f0d] px-3 py-2.5 text-xs text-coral",
        className,
      )}
    >
      <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span>{message}</span>
    </div>
  );
}

export function Empty({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("px-4 py-8 text-center text-xs text-faint", className)}>{children}</div>;
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse bg-deck", className)} />;
}
