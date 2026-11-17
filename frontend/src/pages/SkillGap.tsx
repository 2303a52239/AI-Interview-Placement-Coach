import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getSkillGap, listRoles, getErrorMessage } from "../services/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, Label } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { PageHeader, PageSkeleton, ErrorBox, Empty, Stat } from "@/components/ui/page";
import { titleCase } from "@/lib/utils";

const STATE: Record<string, { label: string; tone: "teal" | "amber" | "clay" | "neutral" }> = {
  verified_strong: { label: "Verified strong", tone: "teal" }, weak: { label: "Weak", tone: "clay" },
  unverified: { label: "Unverified", tone: "amber" }, missing: { label: "Missing", tone: "clay" },
};

export default function SkillGap() {
  const [role, setRole] = useState("");
  const [roles, setRoles] = useState<string[]>([]);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async (r?: string) => {
    setLoading(true); setError("");
    try { const res = await getSkillGap(r); setData(res.data); setRole(res.data.role); } catch (e) { setError(getErrorMessage(e, "Could not load the skill-gap analysis.")); } finally { setLoading(false); }
  };
  useEffect(() => { listRoles().then((r) => setRoles(r.data.roles || [])).catch(() => undefined); load(); }, []);

  if (loading && !data) return <PageSkeleton />;
  if (error && !data) return <ErrorBox message={error} onRetry={() => load()} />;
  const gaps: any[] = data?.gaps || [];

  return (
    <div className="max-w-4xl">
      <PageHeader title="Skill gap analysis" description="Your resume and profile skills compared with what the role needs. Skills you haven't yet demonstrated in an interview or coding attempt are discounted, so a long resume can't hide a gap."
        actions={<Button asChild variant="accent"><Link to="/roadmap">Build a roadmap from this</Link></Button>} />
      <div className="mb-5 max-w-xs"><Label htmlFor="role">Target role</Label>
        <Select id="role" value={role} onChange={(e) => load(e.target.value)}>{(roles.length ? roles : [role]).filter(Boolean).map((r) => <option key={r}>{r}</option>)}</Select></div>
      {data && (<>
        <div className="mb-5 grid gap-3 sm:grid-cols-4">
          <Stat label="Role fit" value={`${Math.round(data.role_fit_score)}%`} />
          {Object.entries(data.summary || {}).map(([k, v]) => <Stat key={k} label={STATE[k]?.label || titleCase(k)} value={v as number} />)}
        </div>
        {!data.has_resume && <p className="mb-4 rounded-card bg-amber-light px-3 py-2 text-sm text-amber-dark">No resume uploaded: only skills in your profile are counted. <Link to="/resume" className="underline">Upload one</Link>.</p>}
        {!data.has_measurements && <p className="mb-4 rounded-card bg-amber-light px-3 py-2 text-sm text-amber-dark">You haven't completed an interview or coding attempt yet, so no skill can show as verified.</p>}
        {gaps.length === 0 ? <Empty title="No skills to analyse" description="Add skills to your profile or upload a resume." /> : (
          <Card><CardHeader><CardTitle>Skills ranked by priority</CardTitle></CardHeader><CardContent className="divide-y divide-paper-line">
            {gaps.map((g) => (
              <div key={g.skill} className="py-3">
                <div className="mb-1 flex flex-wrap items-center justify-between gap-2"><span className="font-medium">{g.skill}</span><span className="flex items-center gap-2"><Badge tone={STATE[g.state]?.tone || "neutral"}>{STATE[g.state]?.label || g.state}</Badge><span className="font-mono text-xs text-ink-faint">{Math.round(g.current)} / {g.target}</span></span></div>
                <Progress value={g.current} tone={g.current >= 70 ? "teal" : g.current >= 40 ? "amber" : "clay"} aria-label={`${g.skill} level`} />
                <p className="mt-1 text-xs text-ink-faint">Evidence: {g.evidence.join("; ")}</p>
                {g.gap > 0 && g.topics?.length > 0 && <p className="mt-0.5 text-xs">Study: {g.topics.join(", ")}</p>}
              </div>
            ))}
          </CardContent></Card>
        )}
        <p className="mt-3 text-xs text-ink-faint">{data.note}</p>
      </>)}
    </div>
  );
}
