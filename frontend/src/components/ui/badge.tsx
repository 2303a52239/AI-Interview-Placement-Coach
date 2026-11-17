import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "@/lib/utils";

const badgeVariants = cva("inline-flex items-center rounded px-2 py-0.5 text-xs font-medium", {
  variants: {
    tone: {
      neutral: "bg-paper-line text-ink-soft",
      amber: "bg-amber-light text-amber-dark",
      teal: "bg-teal-light text-teal-dark",
      clay: "bg-clay/15 text-clay",
    },
  },
  defaultVariants: { tone: "neutral" },
});

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}
export const Badge = ({ className, tone, ...p }: BadgeProps) => <span className={cn(badgeVariants({ tone }), className)} {...p} />;
