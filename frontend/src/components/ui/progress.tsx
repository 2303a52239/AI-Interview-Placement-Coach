import * as React from "react";
import * as ProgressPrimitive from "@radix-ui/react-progress";
import { cn } from "@/lib/utils";

export const Progress = ({ value = 0, className, tone = "teal", ...p }: { value?: number; className?: string; tone?: "teal" | "amber" | "clay" } & React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root>) => (
  <ProgressPrimitive.Root value={value} className={cn("relative h-2 w-full overflow-hidden rounded-full bg-paper-line", className)} {...p}>
    <ProgressPrimitive.Indicator
      className={cn("h-full transition-all", tone === "teal" ? "bg-teal" : tone === "amber" ? "bg-amber" : "bg-clay")}
      style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
    />
  </ProgressPrimitive.Root>
);
