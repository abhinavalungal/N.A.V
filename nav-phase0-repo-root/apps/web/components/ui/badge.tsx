import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

const badge = cva(
  "inline-flex items-center gap-1.5 rounded-panel border px-2 py-0.5 text-micro font-medium",
  {
    variants: {
      tone: {
        neutral: "border-hairline bg-raised text-muted",
        positive: "border-positive/40 bg-positive/10 text-positive",
        signal: "border-signal/40 bg-signal/10 text-signal",
        critical: "border-critical/40 bg-critical/10 text-critical",
        primary: "border-primary/40 bg-primary/10 text-primary",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

export type BadgeProps = HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badge>;

export function Badge({ className, tone, ...props }: BadgeProps) {
  return <span className={cn(badge({ tone }), className)} {...props} />;
}
