import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "@/lib/utils";

export const Tabs = TabsPrimitive.Root;
export const TabsList = ({ className, ...p }: React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>) => (
  <TabsPrimitive.List className={cn("mb-5 inline-flex max-w-full flex-wrap gap-1 rounded-card border border-paper-line bg-paper-panel p-1", className)} {...p} />
);
export const TabsTrigger = ({ className, ...p }: React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>) => (
  <TabsPrimitive.Trigger
    className={cn("rounded px-3 py-1.5 text-sm text-ink-faint transition-colors focus-ring data-[state=active]:bg-amber data-[state=active]:font-medium data-[state=active]:text-[rgb(23_27_31)]", className)}
    {...p}
  />
);
export const TabsContent = ({ className, ...p }: React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>) => (
  <TabsPrimitive.Content className={cn("focus-ring", className)} {...p} />
);
