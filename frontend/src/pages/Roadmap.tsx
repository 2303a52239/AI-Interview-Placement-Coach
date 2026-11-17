import { useEffect, useState } from "react";
import { RefreshCw, CheckCircle2, Circle } from "lucide-react";
import { getRoadmap, createRoadmap, refreshRoadmap, setTaskStatus, listRoles, getErrorMessage } from "../services/api";
import { useToast } from "../context/ToastContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input, Select, Label } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { PageHeader, PageSkeleton, Stat } from "@/components/ui/page";
import { titleCase } from "@/lib/utils";

const TYPE_TONE: Record<string, "teal" | "amber" | "clay" | "neutral"> = { study: "teal", revision: "amber", mock: "clay", practice: "neutral" };

export default function Roadmap() {
  const { showToast } = useToast();
  const [rm, setRm] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [weeks, setWeeks] = useState(4);
  const [hours, setHours] = useState(2);
  const [role, setRole] = useState("");
  const [roles, setRoles] = useState<string[]>([]);
  const [week, setWeek] = useState(1);

  useEffect(() => {
    listRoles().then((r) => setRoles(r.data.roles || [])).catch(() => undefined);
    getRoadmap().then((r) => setRm(r.data)).catch(() => setRm(null)).finally(() => setLoading(false));
  }, []);

  const generate = async () => {
    setBusy(true);
    try { const r = await createRoadmap({ weeks, hours_per_day: hours, role: role || undefined }); setRm(r.data); setWeek(1); showToast("Roadmap generated from your current skill gaps.", "success"); }
    catch (e) { showToast(getErrorMessage(e, "Could not generate the roadmap."), "error"); } finally { setBusy(false); }
  };
  const refresh = async () => {
    setBusy(true);
    try {
      const r = await refreshRoadmap(); setRm(r.data.roadmap); const c = r.data.changes;
      showToast(`Updated from your latest results: ${c.added} task(s) added, ${c.removed} removed.`, "success");
    } catch (e) { showToast(getErrorMessage(e), "error"); } finally { setBusy(false); }
  };
  const toggle = async (t: any) => {
    const next = t.status === "done" ? "todo" : "done";
    try {
      const r = await setTaskStatus(t.id, next);
      setRm((old: any) => ({ ...old, progress: r.data.progress, tasks: old.tasks.map((x: any) => (x.id === t.id ? r.data.task : x)), today: old.today.map((x: any) => (x.id === t.id ? r.data.task : x)) }));
    } catch (e) { showToast(getErrorMessage(e), "error"); }
  };

  if (loading) return <PageSkeleton />;
  const Task = ({ t }: { t: any }) => (
    <li className="flex items-start gap-3 py-2">
      <button type="button" role="checkbox" aria-checked={t.status === "done"} aria-label={`Mark "${t.title}" ${t.status === "done" ? "not done" : "done"}`} onClick={() => toggle(t)} className="mt-0.5 text-teal">{t.status === "done" ? <CheckCircle2 size={18} /> : <Circle size={18} />}</button>
      <div className="min-w-0 flex-1"><p className={t.status === "done" ? "text-ink-faint line-through" : "font-medium"}>{t.title}</p><p className="text-xs text-ink-faint">{t.description}</p></div>
      <div className="flex shrink-0 flex-col items-end gap-1"><Badge tone={TYPE_TONE[t.task_type] || "neutral"}>{t.task_type}</Badge><span className="font-mono text-xs text-ink-faint">{t.due_date.slice(5)} · {t.est_minutes}m</span></div>
    </li>
  );

  const weekTasks = rm ? rm.tasks.filter((t: any) => t.week_index === week) : [];
  return (
    <div className="max-w-4xl">
      <PageHeader title="Preparation roadmap" description="Daily tasks and spaced revisions generated from your skill gaps. Refresh after new interviews to drop topics you've mastered."
        actions={rm && <Button variant="outline" onClick={refresh} disabled={busy}><RefreshCw size={15} /> Update from latest results</Button>} />
      <Card className="mb-5"><CardHeader><CardTitle>{rm ? "Generate a new roadmap" : "Generate your roadmap"}</CardTitle></CardHeader><CardContent className="flex flex-wrap items-end gap-3">
        <div><Label htmlFor="weeks">Weeks</Label><Select id="weeks" value={weeks} onChange={(e) => setWeeks(Number(e.target.value))}>{[2, 4, 6, 8, 12].map((w) => <option key={w}>{w}</option>)}</Select></div>
        <div><Label htmlFor="hours">Hours per day</Label><Input id="hours" type="number" min={0.5} max={8} step={0.5} value={hours} onChange={(e) => setHours(Number(e.target.value))} className="w-28" /></div>
        <div><Label htmlFor="rrole">Role</Label><Select id="rrole" value={role} onChange={(e) => setRole(e.target.value)}><option value="">From my profile</option>{roles.map((r) => <option key={r}>{r}</option>)}</Select></div>
        <Button variant="accent" onClick={generate} disabled={busy}>{busy ? "Working..." : rm ? "Replace roadmap" : "Generate roadmap"}</Button>
      </CardContent></Card>
      {rm && (<>
        <div className="mb-5 grid gap-3 sm:grid-cols-4">
          <Stat label="Progress" value={`${Math.round(rm.progress.percent)}%`} hint={`${rm.progress.done} of ${rm.progress.total} tasks`} />
          <Stat label="Due today" value={rm.progress.due_today} /><Stat label="Overdue" value={rm.progress.overdue} /><Stat label="Role" value={<span className="text-base">{rm.target_role}</span>} />
        </div>
        <Progress value={rm.progress.percent} className="mb-5" aria-label="Roadmap progress" />
        <Card className="mb-5"><CardHeader><CardTitle>Today</CardTitle></CardHeader><CardContent>{rm.today.length ? <ul className="divide-y divide-paper-line">{rm.today.map((t: any) => <Task key={t.id} t={t} />)}</ul> : <p className="text-sm text-ink-faint">Nothing scheduled for today.</p>}</CardContent></Card>
        <Card><CardHeader><CardTitle>Weekly plan</CardTitle></CardHeader><CardContent>
          <div className="mb-3 flex flex-wrap gap-2">{Array.from({ length: rm.weeks }, (_, i) => i + 1).map((w) => <Button key={w} size="sm" variant={w === week ? "accent" : "outline"} onClick={() => setWeek(w)}>Week {w}</Button>)}</div>
          {rm.weekly_targets[week - 1] && <p className="mb-2 text-sm"><span className="font-medium">Focus:</span> {rm.weekly_targets[week - 1].focus_topics.map(titleCase).join(", ")}. <span className="text-ink-faint">{rm.weekly_targets[week - 1].target}</span></p>}
          <ul className="divide-y divide-paper-line">{weekTasks.map((t: any) => <Task key={t.id} t={t} />)}</ul>
        </CardContent></Card>
      </>)}
    </div>
  );
}
