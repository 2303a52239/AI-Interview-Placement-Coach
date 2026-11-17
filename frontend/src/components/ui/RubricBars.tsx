import { Progress } from "./progress";
import { titleCase } from "@/lib/utils";

export type Rubric = Record<string, { score: number; rationale?: string }>;
const tone = (s: number) => (s >= 75 ? "teal" : s >= 50 ? "amber" : "clay") as "teal" | "amber" | "clay";

export function RubricBars({ rubric }: { rubric: Rubric }) {
  const entries = Object.entries(rubric || {});
  if (!entries.length) return null;
  return (
    <ul className="space-y-2" aria-label="Rubric scores">
      {entries.map(([k, v]) => (
        <li key={k}>
          <div className="mb-0.5 flex justify-between text-xs"><span>{titleCase(k)}</span><span className="font-mono">{Math.round(v.score)}</span></div>
          <Progress value={v.score} tone={tone(v.score)} aria-label={titleCase(k)} />
          {v.rationale && <p className="mt-0.5 text-xs text-ink-faint">{v.rationale}</p>}
        </li>
      ))}
    </ul>
  );
}
