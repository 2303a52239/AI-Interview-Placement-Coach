import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, LineChart, Line, Cell } from "recharts";
import { getAnalytics, getErrorMessage } from "../services/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RubricBars } from "@/components/ui/RubricBars";
import { PageHeader, PageSkeleton, ErrorBox, Empty, Stat } from "@/components/ui/page";
import { titleCase } from "@/lib/utils";

const TIP = { borderRadius: 6, border: "1px solid rgb(var(--line))", background: "rgb(var(--panel))", color: "rgb(var(--ink))", fontSize: 12 };
const AX = { fontSize: 11, fill: "rgb(var(--ink-faint))" };
const col = (s: number) => (s >= 75 ? "rgb(var(--teal))" : s >= 50 ? "rgb(var(--amber))" : "rgb(var(--clay))");

export default function Analytics() {
  const [d, setD] = useState<any>(null);
  const [error, setError] = useState("");
  const load = () => { setError(""); getAnalytics().then((r) => setD(r.data)).catch((e) => setError(getErrorMessage(e, "Could not load analytics."))); };
  useEffect(load, []);
  if (error) return <ErrorBox message={error} onRetry={load} />;
  if (!d) return <PageSkeleton />;
  if (!d.has_data) return (<div className="max-w-3xl"><PageHeader title="Analytics" /><Empty title="No data to chart yet" description="Charts are built only from your completed interviews and coding submissions. Complete one to start." action={<div className="flex gap-2"><Button asChild variant="accent"><Link to="/interview/technical">Start an interview</Link></Button><Button asChild variant="outline"><Link to="/coding">Solve a problem</Link></Button></div>} /></div>);
  const o = d.overview;
  const rubric = Object.fromEntries(Object.entries(d.rubric || {}).map(([k, v]) => [k, { score: v as number }]));
  const topics = d.topics.map((t: any) => ({ ...t, label: titleCase(t.topic) }));
  return (
    <div className="max-w-5xl">
      <PageHeader title="Analytics" description="Everything here is computed from your own attempts. Nothing is estimated or filled in." />
      <div className="mb-5 grid gap-3 sm:grid-cols-5">
        <Stat label="Interviews" value={o.interviews_completed} /><Stat label="Avg interview score" value={o.avg_interview_score ?? "—"} />
        <Stat label="Coding submissions" value={o.coding_submissions} /><Stat label="Problems solved" value={o.problems_solved} /><Stat label="Day streak" value={o.streak.current} hint={`longest ${o.streak.longest} · ${o.active_days_90} active days / 90`} />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Card><CardHeader><CardTitle>Weekly score trend</CardTitle></CardHeader><CardContent>
          {d.trend.length < 2 ? <p className="py-10 text-center text-sm text-ink-faint">A trend needs at least two weeks of activity.</p> : (
            <ResponsiveContainer width="100%" height={220}><LineChart data={d.trend}><CartesianGrid stroke="rgb(var(--line))" vertical={false} /><XAxis dataKey="week" tick={AX} /><YAxis domain={[0, 100]} tick={AX} width={28} /><Tooltip contentStyle={TIP} /><Line dataKey="overall" name="Score" stroke="rgb(var(--teal))" strokeWidth={2} dot={{ r: 3 }} /></LineChart></ResponsiveContainer>)}
        </CardContent></Card>
        <Card><CardHeader><CardTitle>Topic strength</CardTitle><CardDescription>Interview and coding scores combined</CardDescription></CardHeader><CardContent>
          {topics.length === 0 ? <p className="py-10 text-center text-sm text-ink-faint">No topic scores yet.</p> : (
            <ResponsiveContainer width="100%" height={Math.max(180, topics.length * 30)}><BarChart data={topics} layout="vertical" margin={{ left: 30 }}><CartesianGrid stroke="rgb(var(--line))" horizontal={false} /><XAxis type="number" domain={[0, 100]} tick={AX} /><YAxis type="category" dataKey="label" tick={AX} width={100} /><Tooltip contentStyle={TIP} /><Bar dataKey="score" radius={[0, 4, 4, 0]}>{topics.map((t: any) => <Cell key={t.topic} fill={col(t.score)} />)}</Bar></BarChart></ResponsiveContainer>)}
        </CardContent></Card>
        <Card><CardHeader><CardTitle>Answer rubric (average)</CardTitle></CardHeader><CardContent>{Object.keys(rubric).length ? <RubricBars rubric={rubric as any} /> : <p className="py-6 text-center text-sm text-ink-faint">No rubric-scored answers yet.</p>}</CardContent></Card>
        <Card><CardHeader><CardTitle>Coding</CardTitle></CardHeader><CardContent className="space-y-2 text-sm">
          {d.coding.submissions === 0 ? <p className="py-6 text-center text-ink-faint">No submissions yet.</p> : (<>
            <div>{Object.entries(d.coding.status).map(([k, v]) => <p key={k} className="flex justify-between"><span>{titleCase(k)}</span><span className="font-mono">{v as number}</span></p>)}</div>
            <p className="pt-2 font-medium">By language</p>{Object.entries(d.coding.by_language).map(([k, v]: any) => <p key={k} className="flex justify-between"><span>{k}</span><span className="font-mono">{v.avg} avg · {v.count}</span></p>)}
            <p className="pt-2 font-medium">By difficulty</p>{Object.entries(d.coding.by_difficulty).map(([k, v]: any) => <p key={k} className="flex justify-between"><span>{titleCase(k)}</span><span className="font-mono">{v.avg} avg · {v.count}</span></p>)}</>)}
        </CardContent></Card>
        <Card className="md:col-span-2"><CardHeader><CardTitle>Voice delivery</CardTitle></CardHeader><CardContent className="text-sm">
          {d.speech.voice_answers === 0 ? <p className="text-ink-faint">No voice answers yet. Turn on Voice interview when starting one to get pace and filler-word feedback.</p> : <p>{d.speech.voice_answers} voice answers · average {d.speech.avg_wpm ?? "—"} words/min · filler ratio {d.speech.avg_filler_ratio !== null ? `${(d.speech.avg_filler_ratio * 100).toFixed(1)}%` : "—"}</p>}
        </CardContent></Card>
      </div>
    </div>
  );
}
