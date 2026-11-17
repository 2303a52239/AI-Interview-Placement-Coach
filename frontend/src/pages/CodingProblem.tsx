import { useEffect, useMemo, useState } from "react";
import { useParams, Link, useSearchParams } from "react-router-dom";
import { ArrowLeft, Play, Send, CheckCircle2, XCircle, Timer } from "lucide-react";
import CodeEditor from "../components/ui/CodeEditor";
import { getCodingQuestion, submitCode, runCode, listSubmissions, getAssessment, finishAssessment, getErrorMessage } from "../services/api";
import { useToast } from "../context/ToastContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select } from "@/components/ui/input";
import { PageSkeleton, ErrorBox } from "@/components/ui/page";
import { titleCase } from "@/lib/utils";

const TONE: Record<string, "teal" | "amber" | "clay"> = { easy: "teal", medium: "amber", hard: "clay" };
const LANGS = [{ v: "python", l: "Python", f: "solution.py" }, { v: "java", l: "Java", f: "Solution.java" }, { v: "cpp", l: "C++", f: "solution.cpp" }];
const mmss = (s: number) => `${String(Math.floor(Math.max(0, s) / 60)).padStart(2, "0")}:${String(Math.max(0, s) % 60).padStart(2, "0")}`;
const STATUS_TONE: Record<string, "teal" | "amber" | "clay"> = { passed: "teal", partial: "amber" };

export default function CodingProblem() {
  const { id } = useParams();
  const [sp] = useSearchParams();
  const assessmentId = sp.get("assessment") ? Number(sp.get("assessment")) : undefined;
  const { showToast } = useToast();
  const [q, setQ] = useState<any>(null);
  const [lang, setLang] = useState("python");
  const [codes, setCodes] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<"" | "run" | "submit">("");
  const [run, setRun] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [assessment, setAssessment] = useState<any>(null);
  const [remaining, setRemaining] = useState<number | null>(null);

  const loadHistory = () => listSubmissions({ question_id: Number(id), page_size: 10 }).then((r) => setHistory(r.data.items || r.data)).catch(() => undefined);

  useEffect(() => {
    setLoading(true); setError(""); setRun(null); setResult(null);
    getCodingQuestion(id as string).then((r) => {
      setQ(r.data);
      const sc = r.data.starter_codes || {};
      setCodes({ python: sc.python || "", java: sc.java || r.data.starter_code || "", cpp: sc.cpp || "" });
    }).catch((e) => setError(getErrorMessage(e, "Could not load this coding question."))).finally(() => setLoading(false));
    loadHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (!assessmentId) { setAssessment(null); setRemaining(null); return; }
    getAssessment(assessmentId).then((r) => { setAssessment(r.data); setRemaining(r.data.remaining_seconds); }).catch(() => undefined);
  }, [assessmentId]);

  useEffect(() => {
    if (remaining === null) return;
    const t = setInterval(() => setRemaining((s) => (s === null ? s : Math.max(0, s - 1))), 1000);
    return () => clearInterval(t);
  }, [remaining === null]);

  const expired = assessment?.status === "in_progress" && remaining === 0;
  const code = codes[lang] ?? "";
  const meta = useMemo(() => LANGS.find((x) => x.v === lang)!, [lang]);

  const doRun = async () => {
    setBusy("run"); setRun(null); setResult(null);
    try { setRun((await runCode({ question_id: Number(id), source_code: code, language: lang })).data); } catch (e) { showToast(getErrorMessage(e, "Could not run your code."), "error"); } finally { setBusy(""); }
  };
  const doSubmit = async () => {
    setBusy("submit"); setRun(null); setResult(null);
    try {
      const r = await submitCode({ question_id: Number(id), source_code: code, language: lang, assessment_id: assessmentId });
      setResult(r.data); loadHistory();
      if (r.data.status === "passed") showToast("All test cases passed!", "success");
    } catch (e) { showToast(getErrorMessage(e, "Submission failed."), "error"); } finally { setBusy(""); }
  };
  const finish = async () => {
    try { const r = await finishAssessment(assessmentId as number); setAssessment(r.data); setRemaining(0); showToast(`Assessment finished. Score ${Math.round(r.data.score ?? 0)}/100.`, "success"); } catch (e) { showToast(getErrorMessage(e), "error"); }
  };

  if (loading) return <PageSkeleton />;
  if (error || !q) return <ErrorBox message={error || "Not found."} onRetry={() => window.location.reload()} />;

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <Link to="/coding" className="inline-flex items-center gap-1 text-sm text-ink-faint hover:text-ink"><ArrowLeft size={14} /> Back to problems</Link>
        {assessment && (
          <div className="flex flex-wrap items-center gap-2 text-sm" aria-label="Assessment">
            <Badge tone={assessment.status === "in_progress" ? "amber" : "neutral"}>{assessment.title}</Badge>
            {assessment.status === "in_progress" && <span className="flex items-center gap-1 font-mono" role="timer" aria-live="off"><Timer size={14} /> {mmss(remaining ?? 0)}</span>}
            {assessment.questions.map((x: any, i: number) => <Link key={x.id} to={`/coding/${x.id}?assessment=${assessment.id}`}><Badge tone={String(x.id) === id ? "teal" : "neutral"}>Q{i + 1}{assessment.best_scores?.[x.id] != null ? ` · ${Math.round(assessment.best_scores[x.id])}` : ""}</Badge></Link>)}
            {assessment.status === "in_progress" && <Button size="sm" variant="outline" onClick={finish}>Finish assessment</Button>}
          </div>
        )}
      </div>
      {expired && <p className="mb-3 rounded-card bg-clay/10 px-3 py-2 text-sm text-clay" role="alert">Time is up. Further submissions for this assessment are rejected.</p>}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="h-fit p-6">
          <div className="mb-3 flex items-center justify-between"><h1 className="font-display text-xl">{q.title}</h1><Badge tone={TONE[q.difficulty]}>{q.difficulty}</Badge></div>
          <div className="mb-4 flex flex-wrap gap-1"><Badge>{titleCase(q.topic_tag)}</Badge>{q.company_tags?.map((c: string) => <Badge key={c} tone="teal">{titleCase(c)}</Badge>)}</div>
          <p className="mb-5 whitespace-pre-wrap text-sm leading-relaxed text-ink-soft">{q.problem_statement}</p>
          <div className="space-y-4 text-sm">
            {[["Input format", q.input_format], ["Output format", q.output_format], ["Constraints", q.constraints]].map(([k, v]) => v && <div key={k}><p className="mb-1 font-mono text-xs uppercase text-ink-faint">{k}</p><p className="text-ink-soft">{v}</p></div>)}
            <div className="grid grid-cols-2 gap-4">
              <div><p className="mb-1 font-mono text-xs uppercase text-ink-faint">Sample input</p><pre className="whitespace-pre-wrap rounded-card border border-paper-line bg-paper p-3 text-xs">{q.sample_input}</pre></div>
              <div><p className="mb-1 font-mono text-xs uppercase text-ink-faint">Sample output</p><pre className="whitespace-pre-wrap rounded-card border border-paper-line bg-paper p-3 text-xs">{q.sample_output}</pre></div>
            </div>
            <p className="text-xs text-ink-faint">{q.visible_tests} visible and {q.hidden_tests} hidden test cases. Hidden test contents are never shown.</p>
          </div>
        </Card>

        <div className="space-y-4">
          <Card className="overflow-hidden">
            <div className="flex items-center justify-between bg-ink px-4 py-2 font-mono text-xs text-white/70">
              <span>{meta.f}</span>
              <Select aria-label="Language" className="h-7 w-28 py-0 text-xs" value={lang} onChange={(e) => setLang(e.target.value)}>{LANGS.map((l) => <option key={l.v} value={l.v}>{l.l}</option>)}</Select>
            </div>
            <CodeEditor value={code} onChange={(v: string) => setCodes((c) => ({ ...c, [lang]: v }))} language={lang} height="380px" />
          </Card>
          <div className="flex gap-2">
            <Button variant="outline" onClick={doRun} disabled={!!busy || expired}><Play size={15} /> {busy === "run" ? "Running..." : "Run sample"}</Button>
            <Button variant="accent" onClick={doSubmit} disabled={!!busy || expired}><Send size={15} /> {busy === "submit" ? "Judging..." : "Submit"}</Button>
          </div>

          {run && (
            <Card className="p-4 text-sm" aria-live="polite">
              <div className="mb-2 flex items-center gap-2">{run.passed ? <CheckCircle2 className="text-teal" size={16} /> : <XCircle className="text-clay" size={16} />}<span className="font-medium">{run.passed ? "Sample passed" : titleCase(run.status)}</span></div>
              {run.compile_output && <pre className="mb-2 whitespace-pre-wrap rounded-card bg-paper p-2 text-xs text-clay">{run.compile_output}</pre>}
              <div className="grid grid-cols-2 gap-3 text-xs"><div><p className="text-ink-faint">Expected</p><pre className="whitespace-pre-wrap">{run.expected_output}</pre></div><div><p className="text-ink-faint">Your output</p><pre className="whitespace-pre-wrap">{run.actual_output}</pre></div></div>
            </Card>
          )}

          {result && (
            <Card className="p-4 text-sm" aria-live="polite">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <span className="flex items-center gap-2 font-medium">{result.status === "passed" ? <CheckCircle2 className="text-teal" size={16} /> : <XCircle className="text-clay" size={16} />}<Badge tone={STATUS_TONE[result.status] || "clay"}>{titleCase(result.status)}</Badge></span>
                <span className="font-mono">{result.passed_test_cases}/{result.total_test_cases} tests · score {Math.round(result.score)}</span>
              </div>
              {result.hidden_total > 0 && <p className="mb-2 text-xs text-ink-faint">Hidden tests: {result.hidden_passed}/{result.hidden_total} passed</p>}
              {result.compile_output && <pre className="mb-2 whitespace-pre-wrap rounded-card bg-paper p-2 text-xs text-clay">{result.compile_output}</pre>}
              <p className="mb-2">{result.ai_feedback}</p>
              <p className="mb-2 font-mono text-xs text-ink-faint">Estimated complexity: time {result.time_complexity_estimate}, space {result.space_complexity_estimate}. {result.complexity_note}</p>
              <ul className="divide-y divide-paper-line text-xs">{result.test_case_results.map((t: any, i: number) => (
                <li key={i} className="py-1.5"><span className="flex items-center gap-2">{t.passed ? <CheckCircle2 size={13} className="text-teal" /> : <XCircle size={13} className="text-clay" />}{t.hidden ? `Hidden test ${i + 1}` : `Test ${i + 1}`}<span className="ml-auto font-mono text-ink-faint">{t.status} · {Math.round(t.time_ms)}ms</span></span>
                  {!t.hidden && !t.passed && <span className="mt-1 block font-mono text-ink-faint">in: {t.input} | expected: {t.expected_output} | got: {t.actual_output}</span>}</li>))}</ul>
              <p className="mt-2 text-xs text-ink-faint">Sandbox: {result.sandbox || "n/a"}</p>
            </Card>
          )}

          <Card><CardHeader><CardTitle className="text-base">Submission history</CardTitle></CardHeader><CardContent>
            {history.length === 0 ? <p className="text-sm text-ink-faint">No submissions for this problem yet.</p> : <ul className="divide-y divide-paper-line text-sm">{history.map((h) => <li key={h.id} className="flex items-center justify-between py-1.5"><span>{new Date(h.submitted_at).toLocaleString()} · {h.language}</span><span className="font-mono text-xs">{h.passed_test_cases}/{h.total_test_cases} · {Math.round(h.score)}</span></li>)}</ul>}
          </CardContent></Card>
        </div>
      </div>
    </div>
  );
}
