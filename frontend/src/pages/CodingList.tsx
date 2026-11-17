import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Code2, ArrowRight, Timer } from "lucide-react";
import { listCodingQuestions, listAssessments, startAssessment, getErrorMessage } from "../services/api";
import { useToast } from "../context/ToastContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input, Select, Label } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { PageHeader, PageSkeleton, ErrorBox, Empty } from "@/components/ui/page";
import { titleCase } from "@/lib/utils";

const TONE: Record<string, "teal" | "amber" | "clay"> = { easy: "teal", medium: "amber", hard: "clay" };
const COMPANIES = ["", "microsoft", "google", "amazon", "accenture", "infosys", "tcs", "deloitte"];

export default function CodingList() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [qs, setQs] = useState<any[]>([]);
  const [assessments, setAssessments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [topic, setTopic] = useState("");
  const [company, setCompany] = useState("");
  const [search, setSearch] = useState("");
  const [shown, setShown] = useState(24);
  const [cfg, setCfg] = useState({ num_questions: 2, duration_minutes: 45, difficulty: "", company: "" });
  const [starting, setStarting] = useState(false);

  const load = async () => {
    setLoading(true); setError("");
    try {
      const [a, b] = await Promise.all([listCodingQuestions({ difficulty: difficulty || undefined, topic: topic || undefined, company: company || undefined }), listAssessments()]);
      setQs(a.data); setAssessments(b.data);
    } catch (e) { setError(getErrorMessage(e, "Could not load coding questions.")); } finally { setLoading(false); }
  };
  useEffect(() => { load(); setShown(24); }, [difficulty, topic, company]);
  useEffect(() => { setShown(24); }, [search]);

  const begin = async () => {
    setStarting(true);
    try {
      const r = await startAssessment({ num_questions: cfg.num_questions, duration_minutes: cfg.duration_minutes, difficulty: cfg.difficulty || undefined, company: cfg.company || undefined });
      navigate(`/coding/${r.data.questions[0].id}?assessment=${r.data.id}`);
    } catch (e) { showToast(getErrorMessage(e, "Could not start the assessment."), "error"); } finally { setStarting(false); }
  };

  if (loading && !qs.length && !assessments.length) return <PageSkeleton />;
  if (error && !qs.length) return <ErrorBox message={error} onRetry={load} />;
  const topics = [...new Set(qs.map((q) => q.topic_tag))];
  const filtered = qs.filter((q) => !search.trim() || q.title.toLowerCase().includes(search.trim().toLowerCase()));
  const open = assessments.filter((a) => a.status === "in_progress");

  return (
    <div className="max-w-5xl">
      <PageHeader title="Coding assessment" description="Solve problems in Python, Java or C++. Your code runs in an isolated container against visible and hidden test cases." />
      <Tabs defaultValue="practice">
        <TabsList className="mb-4"><TabsTrigger value="practice">Practice</TabsTrigger><TabsTrigger value="timed">Timed assessment</TabsTrigger></TabsList>
        <TabsContent value="practice">
          <div className="mb-4 flex flex-wrap gap-3">
            <div><Label htmlFor="fs">Search</Label><Input id="fs" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Title contains..." className="w-48" /></div>
            <div><Label htmlFor="fd">Difficulty</Label><Select id="fd" value={difficulty} onChange={(e) => setDifficulty(e.target.value)}><option value="">All</option>{["easy", "medium", "hard"].map((d) => <option key={d}>{d}</option>)}</Select></div>
            <div><Label htmlFor="ft">Topic</Label><Select id="ft" value={topic} onChange={(e) => setTopic(e.target.value)}><option value="">All</option>{topics.map((d) => <option key={d} value={d}>{titleCase(d)}</option>)}</Select></div>
            <div><Label htmlFor="fc">Company tag</Label><Select id="fc" value={company} onChange={(e) => setCompany(e.target.value)}>{COMPANIES.map((d) => <option key={d} value={d}>{d ? titleCase(d) : "All"}</option>)}</Select></div>
          </div>
          {filtered.length === 0 ? <Empty title="No problems match" description="Clear a filter to see more." /> : (
            <><p className="mb-2 text-xs text-ink-faint">{filtered.length} problems</p><div className="grid gap-4 md:grid-cols-2">{filtered.slice(0, shown).map((q) => (
              <Link key={q.id} to={`/coding/${q.id}`}><Card className="h-full p-5 transition-colors hover:border-amber">
                <div className="mb-2 flex items-center justify-between"><Code2 size={18} className="text-amber-dark" /><Badge tone={TONE[q.difficulty] || "neutral"}>{q.difficulty}</Badge></div>
                <h3 className="mb-1 font-medium">{q.title}</h3><p className="mb-3 line-clamp-2 text-sm text-ink-faint">{q.problem_statement}</p>
                <div className="flex items-center justify-between"><span className="flex flex-wrap gap-1"><Badge>{titleCase(q.topic_tag)}</Badge>{q.company_tags?.slice(0, 2).map((c: string) => <Badge key={c} tone="teal">{titleCase(c)}</Badge>)}</span><span className="flex items-center gap-1 text-sm text-amber-dark">Solve <ArrowRight size={14} /></span></div>
              </Card></Link>))}</div>{filtered.length > shown && <div className="mt-4 text-center"><Button variant="outline" onClick={() => setShown((n) => n + 24)}>Show more ({filtered.length - shown} left)</Button></div>}</>)}
        </TabsContent>
        <TabsContent value="timed" className="space-y-4">
          {open.length > 0 && <Card><CardHeader><CardTitle>In progress</CardTitle></CardHeader><CardContent>{open.map((a) => <div key={a.id} className="flex items-center justify-between py-1 text-sm"><span>{a.title} · {Math.ceil(a.remaining_seconds / 60)} min left</span><Button asChild size="sm" variant="accent"><Link to={`/coding/${a.questions[0].id}?assessment=${a.id}`}>Resume</Link></Button></div>)}</CardContent></Card>}
          <Card><CardHeader><CardTitle>Start a timed assessment</CardTitle><CardDescription>The deadline is enforced by the server. Submissions after time is up are rejected.</CardDescription></CardHeader><CardContent className="flex flex-wrap items-end gap-3">
            <div><Label htmlFor="nq">Problems</Label><Select id="nq" value={cfg.num_questions} onChange={(e) => setCfg({ ...cfg, num_questions: Number(e.target.value) })}>{[1, 2, 3, 4, 5].map((n) => <option key={n}>{n}</option>)}</Select></div>
            <div><Label htmlFor="dm">Minutes</Label><Select id="dm" value={cfg.duration_minutes} onChange={(e) => setCfg({ ...cfg, duration_minutes: Number(e.target.value) })}>{[15, 30, 45, 60, 90].map((n) => <option key={n}>{n}</option>)}</Select></div>
            <div><Label htmlFor="ad">Difficulty</Label><Select id="ad" value={cfg.difficulty} onChange={(e) => setCfg({ ...cfg, difficulty: e.target.value })}><option value="">Any</option>{["easy", "medium", "hard"].map((d) => <option key={d}>{d}</option>)}</Select></div>
            <div><Label htmlFor="ac">Company tag</Label><Select id="ac" value={cfg.company} onChange={(e) => setCfg({ ...cfg, company: e.target.value })}>{COMPANIES.map((d) => <option key={d} value={d}>{d ? titleCase(d) : "Any"}</option>)}</Select></div>
            <Button variant="accent" onClick={begin} disabled={starting}><Timer size={15} /> {starting ? "Starting..." : "Start assessment"}</Button>
          </CardContent></Card>
          {assessments.filter((a) => a.status !== "in_progress").length > 0 && <Card><CardHeader><CardTitle>Past assessments</CardTitle></CardHeader><CardContent className="divide-y divide-paper-line">{assessments.filter((a) => a.status !== "in_progress").map((a) => <div key={a.id} className="flex justify-between py-2 text-sm"><span>{a.title} <Badge>{a.status}</Badge></span><span className="font-mono">{a.score != null ? `${Math.round(a.score)}/100` : "—"}</span></div>)}</CardContent></Card>}
        </TabsContent>
      </Tabs>
    </div>
  );
}
