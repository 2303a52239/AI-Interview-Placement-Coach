import * as React from "react";
import { AlertTriangle, Inbox, Loader2 } from "lucide-react";
import { Button } from "./button";
import { Card } from "./card";
import { Skeleton } from "./skeleton";

export const PageHeader = ({ title, description, actions, eyebrow }: { title: string; description?: string; actions?: React.ReactNode; eyebrow?: string }) => (
  <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
    <div>
      {eyebrow && <p className="mb-1 text-sm font-medium text-teal">{eyebrow}</p>}
      <h1 className="font-display text-2xl font-medium">{title}</h1>
      {description && <p className="mt-1 max-w-2xl text-sm text-ink-faint">{description}</p>}
    </div>
    {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
  </div>
);

export const Spinner = ({ label = "Loading..." }: { label?: string }) => (
  <div role="status" className="flex items-center justify-center gap-2 py-16 text-ink-faint">
    <Loader2 className="animate-spin" size={18} /> <span className="text-sm">{label}</span>
  </div>
);

export const PageSkeleton = () => (
  <div className="space-y-4" aria-busy="true"><Skeleton className="h-8 w-64" /><div className="grid gap-4 md:grid-cols-3"><Skeleton className="h-32" /><Skeleton className="h-32" /><Skeleton className="h-32" /></div><Skeleton className="h-64" /></div>
);

export const ErrorBox = ({ message, onRetry }: { message: string; onRetry?: () => void }) => (
  <Card className="flex flex-col items-center gap-3 p-8 text-center" role="alert">
    <AlertTriangle className="text-clay" /> <p className="text-sm">{message}</p>
    {onRetry && <Button variant="outline" size="sm" onClick={onRetry}>Try again</Button>}
  </Card>
);

export const Empty = ({ title, description, action }: { title: string; description?: string; action?: React.ReactNode }) => (
  <Card className="flex flex-col items-center gap-2 p-10 text-center">
    <Inbox className="text-ink-faint" /> <p className="font-medium">{title}</p>
    {description && <p className="max-w-md text-sm text-ink-faint">{description}</p>}
    {action}
  </Card>
);

/** Honest banner shown wherever scores come from the rule-based mock instead of a language model. */
export const SimulatedNote = ({ simulated }: { simulated?: boolean }) =>
  simulated ? (
    <p className="rounded-card bg-amber-light px-3 py-2 text-xs text-amber-dark">
      Mock AI mode: this was scored by built-in rules, not by a language model. Set AI_PROVIDER=openai with an API key for model-based evaluation.
    </p>
  ) : null;

export function Stat({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <Card className="p-4">
      <p className="text-xs text-ink-faint">{label}</p>
      <p className="mt-1 font-mono text-2xl">{value}</p>
      {hint && <p className="mt-1 text-xs text-ink-faint">{hint}</p>}
    </Card>
  );
}
