import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { getInterviewDetail, getErrorMessage } from "../services/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RubricBars } from "@/components/ui/RubricBars";
import { PageHeader, PageSkeleton, ErrorBox, SimulatedNote, Stat } from "@/components/ui/page";
import { titleCase } from "@/lib/utils";

const tone = (d: string) => (d === "hard" ? "clay" : d === "medium" ? "amber" : "teal") as "clay" | "amber" | "teal";

export default function InterviewDetail() {
  const { id } = useParams();
  const [d, setD] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true); setError("");
    try { setD((await getInterviewDetail(id as string)).data); } catch (e) { setError(getErrorMessage(e, "Could not load this interview.")); } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [id]);

  if (loading) return <PageSkeleton />;
  if (error || !d) return <ErrorBox message={error || "Not found."} onRetry={load} />;
  let n = 0;
  return (
    <div className="max-w-4xl">
      <Link to="/history" className="mb-4 inline-flex items-center gap-1 text-sm text-ink-faint hover:text-ink"><ArrowLeft size={14} /> Back to history</Link>
      <PageHeader title={`${d.interview_type === "hr" ? "HR" : "Technical"} interview`} description={`${new Date(d.started_at).toLocaleString()}${d.topic && d.topic !== "mixed" ? ` · ${titleCase(d.topic)}` : ""}${d.adaptive ? " · adaptive" : ""}`} />
      <SimulatedNote simulated={d.simulated} />
      {d.status === "completed" && (
        <div className="my-4 grid gap-3 sm:grid-cols-3"><Stat label="Overall" value={d.overall_score ?? "—"} /><Stat label="Technical" value={d.technical_score ?? "—"} /><Stat label="Communication" value={d.communication_score ?? "—"} /></div>
      )}
      {d.ai_feedback && (
        <Card className="mb-5"><CardHeader><CardTitle>Overall feedback</CardTitle></CardHeader><CardContent>
          <p className="mb-3 text-sm text-ink-soft">{d.ai_feedback}</p>
          <div className="grid gap-3 sm:grid-cols-2 text-sm">
            <div><p className="mb-1 font-medium">Strengths</p><ul className="list-disc pl-5">{d.strengths.length ? d.strengths.map((s: string) => <li key={s}>{s}</li>) : <li className="list-none text-ink-faint">None noted</li>}</ul></div>
            <div><p className="mb-1 font-medium">Weaknesses</p><ul className="list-disc pl-5">{d.weaknesses.length ? d.weaknesses.map((s: string) => <li key={s}>{s}</li>) : <li className="list-none text-ink-faint">None noted</li>}</ul></div>
          </div>
          {d.recommended_topics.length > 0 && <div className="mt-3 flex flex-wrap gap-2">{d.recommended_topics.map((t: string) => <Badge key={t} tone="amber">{titleCase(t)}</Badge>)}</div>}
        </CardContent></Card>
      )}
      <h2 className="mb-3 font-display text-lg">Questions and answers</h2>
      <div className="space-y-4">
        {d.questions.map((q: any, i: number) => {
          if (!q.is_followup) n += 1;
          return (
            <Card key={i} className="p-5">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <Badge>{q.is_followup ? "Follow-up" : `Q${n}`}</Badge><Badge tone={tone(q.difficulty)}>{q.difficulty}</Badge><Badge>{titleCase(q.skill_tag)}</Badge>
                {q.score != null && <span className="ml-auto font-mono text-sm">{Math.round(q.score)}/100</span>}
              </div>
              <p className="mb-2 font-medium">{q.question_text}</p>
              {q.answer_text ? <p className="mb-3 whitespace-pre-wrap rounded-card bg-paper p-3 text-sm text-ink-soft">{q.answer_text}</p> : <p className="mb-2 text-sm italic text-ink-faint">Not answered.</p>}
              {q.feedback && <p className="mb-3 text-sm">{q.feedback}</p>}
              {q.rubric && Object.keys(q.rubric).length > 0 && <div className="mb-3"><RubricBars rubric={q.rubric} /></div>}
              {q.missing_points?.length > 0 && <p className="mb-2 text-sm"><span className="font-medium">Missed: </span>{q.missing_points.join(", ")}</p>}
              {q.ideal_answer && <details className="text-sm"><summary className="cursor-pointer font-medium">Ideal answer</summary><p className="mt-1 text-ink-soft">{q.ideal_answer}</p></details>}
              {q.speech && <p className="mt-2 font-mono text-xs text-ink-faint">Voice: {q.speech.wpm ?? "-"} wpm · {q.speech.filler_total} fillers · {q.speech.long_pauses} long pauses</p>}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
