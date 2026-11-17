import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { getPerformance, getInterviewHistory, getReadiness, getRoadmap, getAiStatus, getErrorMessage } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { ScoreRing } from "../components/ui/ScoreRing";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { PageHeader, PageSkeleton, ErrorBox } from "@/components/ui/page";
import { titleCase } from "@/lib/utils";

const AX = { fontSize: 11, fill: "rgb(var(--ink-faint))" };

export default function Dashboard() {
  const { user } = useAuth();
  const [perf, setPerf] = useState<any>(null);
  const [recent, setRecent] = useState<any[]>([]);
  const [readiness, setReadiness] = useState<any>(null);
  const [roadmap, setRoadmap] = useState<any>(null);
  const [ai, setAi] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true); setError("");
    try {
      const [p, h] = await Promise.all([getPerformance(), getInterviewHistory()]);
      setPerf(p.data); setRecent(h.data.slice(0, 4));
      getReadiness().then((r) => setReadiness(r.data)).catch(() => undefined);
      getRoadmap().then((r) => setRoadmap(r.data)).catch(() => setRoadmap(null));
      getAiStatus().then((r) => setAi(r.data)).catch(() => undefined);
    } catch (e) { setError(getErrorMessage(e, "Could not load your dashboard.")); } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  if (loading) return <PageSkeleton />;
  if (error || !perf) return <ErrorBox message={error || "No data."} onRetry={load} />;
  const hasActivity = perf.total_interviews > 0 || perf.total_coding_attempts > 0;

  return (
    <div className="max-w-6xl">
      <PageHeader eyebrow={`Welcome back, ${user?.name?.split(" ")[0] || "there"}`} title="Your readiness at a glance" description="Updated every time you complete an interview or coding round." />
      {ai && ai.mode === "mock" && <p className="mb-4 rounded-card bg-amber-light px-3 py-2 text-sm text-amber-dark" role="note">AI mode: <strong>mock</strong>. {ai.note}</p>}
      {ai?.mode === "openai" && <p className="mb-4 text-xs text-ink-faint">AI mode: live model ({ai.model})</p>}

      {!hasActivity && (
        <Card className="mb-6 flex flex-wrap items-center justify-between gap-3 p-6">
          <div><p className="mb-1 font-medium">You haven't taken a mock interview yet</p><p className="text-sm text-ink-faint">Start with an HR or technical round to see your scores here.</p></div>
          <div className="flex gap-3"><Button asChild variant="outline"><Link to="/interview/hr">Start HR round</Link></Button><Button asChild variant="accent"><Link to="/interview/technical">Start technical round</Link></Button></div>
        </Card>
      )}

      {readiness && (
        <Card className="mb-6 p-5"><div className="flex flex-wrap items-center justify-between gap-2"><div><p className="text-sm text-ink-faint">Placement readiness</p><p className="font-mono text-3xl">{Math.round(readiness.score)}<span className="text-sm text-ink-faint"> / 100 · {readiness.band}</span></p></div>
          <div className="text-xs text-ink-faint">{readiness.not_yet_measured?.length > 0 && <p>Not yet measured: {readiness.not_yet_measured.join(", ")}</p>}{readiness.profile_gaps?.length > 0 && <p>Profile gaps: {readiness.profile_gaps.slice(0, 3).join(", ")} · <Link to="/profile" className="text-teal underline">complete profile</Link></p>}</div></div>
          <Progress className="mt-3" value={readiness.score} tone={readiness.score >= 75 ? "teal" : readiness.score >= 55 ? "amber" : "clay"} aria-label="Placement readiness" /></Card>
      )}

      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-5">
        {[["Readiness", perf.overall_readiness], ["Technical", perf.technical_score], ["HR", perf.hr_score], ["Coding", perf.coding_score], ["Communication", perf.communication_score]].map(([l, v]) => (
          <Card key={l as string} className="flex flex-col items-center p-5"><ScoreRing value={v as number} label={l as string} sublabel="" /></Card>))}
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <Card className="md:col-span-2"><CardHeader><CardTitle>Performance trend</CardTitle></CardHeader><CardContent>
          {perf.score_trend.length === 0 ? <p className="py-10 text-center text-sm text-ink-faint">Your trend line appears after your first attempt.</p> : (
            <ResponsiveContainer width="100%" height={220}><LineChart data={perf.score_trend}><CartesianGrid stroke="rgb(var(--line))" vertical={false} /><XAxis dataKey="date" tick={AX} /><YAxis domain={[0, 100]} tick={AX} width={28} /><Tooltip contentStyle={{ borderRadius: 6, border: "1px solid rgb(var(--line))", background: "rgb(var(--panel))", fontSize: 12 }} /><Line type="monotone" dataKey="score" stroke="rgb(var(--amber))" strokeWidth={2} dot={{ r: 3 }} /></LineChart></ResponsiveContainer>)}
        </CardContent></Card>
        <Card><CardHeader><CardTitle>Weak areas</CardTitle></CardHeader><CardContent>
          {perf.weak_topics.length === 0 ? <p className="text-sm text-ink-faint">None identified yet.</p> : <div className="flex flex-wrap gap-2">{perf.weak_topics.map((t: string) => <Badge key={t} tone="clay">{titleCase(t)}</Badge>)}</div>}
          <Button asChild variant="outline" size="sm" className="mt-4"><Link to="/skill-gap">Open skill-gap analysis</Link></Button>
        </CardContent></Card>

        <Card><CardHeader><CardTitle>Today's roadmap</CardTitle></CardHeader><CardContent>
          {!roadmap ? <><p className="mb-3 text-sm text-ink-faint">No roadmap yet.</p><Button asChild variant="accent" size="sm"><Link to="/roadmap">Generate one</Link></Button></> : (<>
            <p className="mb-2 font-mono text-sm">{Math.round(roadmap.progress.percent)}% complete</p>
            {roadmap.today.length === 0 ? <p className="text-sm text-ink-faint">Nothing scheduled today.</p> : <ul className="space-y-1 text-sm">{roadmap.today.slice(0, 4).map((t: any) => <li key={t.id} className={t.status === "done" ? "text-ink-faint line-through" : ""}>{t.title}</li>)}</ul>}
            <Button asChild variant="outline" size="sm" className="mt-3"><Link to="/roadmap">Open roadmap</Link></Button></>)}
        </CardContent></Card>
        <Card className="md:col-span-2"><CardHeader><CardTitle>Recent interviews</CardTitle></CardHeader><CardContent>
          {recent.length === 0 ? <p className="text-sm text-ink-faint">No interviews yet.</p> : <ul className="divide-y divide-paper-line">{recent.map((iv) => <li key={iv.id}><Link to={`/history/${iv.id}`} className="flex items-center justify-between py-2 text-sm hover:text-teal"><span>{iv.interview_type === "hr" ? "HR" : "Technical"} · {new Date(iv.started_at).toLocaleDateString()}</span><span className="font-mono">{iv.overall_score != null ? Math.round(iv.overall_score) : iv.status}</span></Link></li>)}</ul>}
        </CardContent></Card>
      </div>
    </div>
  );
}
