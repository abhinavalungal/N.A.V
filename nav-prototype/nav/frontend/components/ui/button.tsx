"use client";

import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/utils";

const button = cva(
  "inline-flex items-center justify-center gap-2 rounded-sm border text-xs font-medium transition-colors disabled:pointer-events-none disabled:opacity-45",
  {
    variants: {
      variant: {
        primary: "border-brass bg-brass text-abyss hover:bg-brass/85 hover:border-brass/85",
        secondary: "border-hairline bg-deck text-ink hover:border-faint/60 hover:bg-raised",
        ghost: "border-transparent bg-transparent text-dim hover:text-ink hover:bg-deck",
        danger: "border-coral/35 bg-coral/10 text-coral hover:bg-coral/20",
        approve: "border-kelp/35 bg-kelp/10 text-kelp hover:bg-kelp/20",
      },
      size: {
        sm: "h-7 px-2.5",
        md: "h-9 px-3.5",
        lg: "h-10 px-5 text-sm",
      },
    },
    defaultVariants: { variant: "secondary", size: "md" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof button> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button ref={ref} className={cn(button({ variant, size }), className)} {...props} />
  ),
);
Button.displayName = "Button";
