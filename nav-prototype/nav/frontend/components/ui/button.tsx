"use client";

import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/utils";

const button = cva(
  "inline-flex items-center justify-center gap-2 rounded-sm border text-xs font-medium transition-colors disabled:pointer-events-none disabled:opacity-45",
  {
    variants: {
      variant: {
        primary:
          "border-brass bg-brass text-abyss hover:bg-[#f0b45f] hover:border-[#f0b45f]",
        secondary:
          "border-hairline bg-deck text-ink hover:border-[#2c4459] hover:bg-raised",
        ghost: "border-transparent bg-transparent text-dim hover:text-ink hover:bg-deck",
        danger: "border-[#4a2723] bg-[#2a1614] text-coral hover:bg-[#391c19]",
        approve: "border-[#26543f] bg-[#12291f] text-kelp hover:bg-[#173427]",
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
