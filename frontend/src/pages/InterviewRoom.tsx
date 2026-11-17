import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Mic, MicOff, Send, Clock, Flag, Volume2, ArrowRight } from "lucide-react";
import { startInterview, submitInterviewAnswer, completeInterview, getErrorMessage } from "../services/api";
import { useToast } from "../context/ToastContext";
import { useConfirm } from "../context/ConfirmContext";
import { useVoiceInput } from "../hooks/useVoiceInput";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input, Select, Textarea, Label } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { PageHeader, Spinner, SimulatedNote } from "@/components/ui/page";
import { RubricBars } from "@/components/ui/RubricBars";
import { ScoreRing } from "@/components/ui/ScoreRing";
import { titleCase } from "@/lib/utils";

const TYPE_LABELS: Record<string, string> = { hr: "HR Interview", technical: "Technical Interview" };
const TOPICS = ["mixed", "python", "java", "sql", "dsa", "dbms", "os", "cn", "ml", "dl", "nlp", "genai", "llm", "rag", "system_design"];
const TOPIC_NAMES: Record<string, string> = { mixed: "Mixed (personalised)", dsa: "Data Structures & Algorithms", dbms: "DBMS", os: "Operating Systems", cn: "Computer Networks", ml: "Machine Learning", dl: "Deep Learning", nlp: "NLP", genai: "Generative AI", llm: "LLMs", rag: "RAG", system_design: "System Design", sql: "SQL", python: "Python", java: "Java" };
const DIFF_TONE: Record<string, "teal" | "amber" | "clay"> = { easy: "teal", medium: "amber", hard: "clay" };
const clampCount = (v: string | number) => Math.min(30, Math.max(1, Math.round(Number(v)) || 5));
const fmt = (s: number) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

export default function InterviewRoom() {
  const { type = "hr" } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const confirm = useConfirm();

  const [phase, setPhase] = useState<"setup" | "active" | "complete">("setup");
  const [numInput, setNumInput] = useState("5");
  const [topic, setTopic] = useState("mixed");
  const [adaptive, setAdaptive] = useState(false);
  const [voiceMode, setVoiceMode] = useState(false);
  const [interview, setInterview] = useState<any>(null);
  const [current, setCurrent] = useState<any>(null);
  const [answeredMain, setAnsweredMain] = useState(0);
  const [answerText, setAnswerText] = useState("");
  const [inputMode, setInputMode] = useState<"text" | "voice">("text");
  const [feedback, setFeedback] = useState<any>(null);
  const [pendingNext, setPendingNext] = useState<any>(null);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [questionsList, setQuestionsList] = useState<any[]>([]);
  const [answeredAny, setAnsweredAny] = useState(0);

  // voice timing: first/last speech timestamps and the gaps between speech updates
  const spokeAt = useRef<{ first: number | null; last: number | null; pauses: number[] }>({ first: null, last: null, pauses: [] });
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    setPhase("setup"); setInterview(null); setCurrent(null); setAnswerText(""); setFeedback(null); setSummary(null);
    setElapsed(0); setAnsweredMain(0); setAnsweredAny(0); setPendingNext(null); setQuestionsList([]);
  }, [type]);

  useEffect(() => {
    if (phase !== "active") return;
    timer.current = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => { if (timer.current) clearInterval(timer.current); };
  }, [phase]);

  const speech = useVoiceInput({
    onText: (text: string) => {
      const now = Date.now();
      const t = spokeAt.current;
      if (t.first === null) t.first = now;
      else if (t.last !== null && now - t.last > 1500) t.pauses.push((now - t.last) / 1000);
      t.last = now;
      setAnswerText(text);
      setInputMode("voice");
    },
    onError: (m: string) => showToast(m, "error"),
  });

  const speak = (text: string) => {
    if (!("speechSynthesis" in window)) { showToast("Your browser cannot read text aloud.", "error"); return; }
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 0.95;
    window.speechSynthesis.speak(u);
  };

  const showQuestion = (q: any) => {
    setCurrent(q); setAnswerText(""); setInputMode("text"); setFeedback(null);
    spokeAt.current = { first: null, last: null, pauses: [] };
    if (voiceMode) speak(q.question_text);
  };

  const handleStart = async () => {
    setLoading(true);
    try {
      const res = await startInterview({ interview_type: type, num_questions: clampCount(numInput), topic: type === "hr" ? "mixed" : topic, adaptive, voice_mode: voiceMode });
      setInterview(res.data);
      setQuestionsList(res.data.questions);
      setPhase("active"); setElapsed(0); setAnsweredMain(0);
      showQuestion(res.data.questions[0]);
    } catch (err) {
      showToast(getErrorMessage(err, "Could not start the interview."), "error");
    } finally { setLoading(false); }
  };

  const finish = async (id: number) => {
    const res = await completeInterview(id);
    setSummary(res.data); setPhase("complete");
    window.speechSynthesis?.cancel();
  };

  const handleSubmit = async () => {
    if (!answerText.trim()) { showToast("Please type or speak an answer first.", "error"); return; }
    if (speech.listening) speech.stop();
    setLoading(true);
    try {
      const t = spokeAt.current;
      const duration = inputMode === "voice" && t.first && t.last ? Math.max(1, (t.last - t.first) / 1000 + 1) : undefined;
      const res = await submitInterviewAnswer(interview.interview_id, {
        question_id: current.id, answer_text: answerText, input_mode: inputMode,
        duration_seconds: duration, pauses: inputMode === "voice" ? t.pauses : undefined,
      });
      setAnsweredAny((n) => n + 1);
      if (!current.is_followup) setAnsweredMain((n) => n + 1);
      setFeedback(res.data.evaluation);
      setPendingNext(res.data.next_question);
      if (res.data.next_question) setQuestionsList((l) => [...l, res.data.next_question]);
    } catch (err) {
      showToast(getErrorMessage(err, "Could not submit your answer."), "error");
    } finally { setLoading(false); }
  };

  const handleNext = async () => {
    if (pendingNext) { showQuestion(pendingNext); setPendingNext(null); return; }
    setLoading(true);
    try { await finish(interview.interview_id); } catch (err) { showToast(getErrorMessage(err, "Could not complete the interview."), "error"); } finally { setLoading(false); }
  };

  const handleEndEarly = async () => {
    const ok = await confirm({
      title: "End this interview now?",
      message: answeredMain === 0 ? "You haven't answered any questions yet, so there will be no score for this round."
        : `You've answered ${answeredMain} of ${interview.target_questions} questions. Your score will be based on those answers only.`,
      confirmLabel: "End and see results",
    });
    if (!ok) return;
    setLoading(true);
    try { await finish(interview.interview_id); } catch (err) { showToast(getErrorMessage(err, "Could not complete the interview."), "error"); } finally { setLoading(false); }
  };

  const title = TYPE_LABELS[type] || "Interview";

  if (phase === "setup") {
    return (
      <div className="max-w-2xl">
        <PageHeader title={title} description="Answers are scored on a six-criteria rubric. Adaptive mode picks each next question from your previous answer." />
        <Card><CardContent className="space-y-5 pt-5">
          <div>
            <Label htmlFor="num">Number of questions (1-30)</Label>
            <Input id="num" type="number" min={1} max={30} value={numInput} onChange={(e) => setNumInput(e.target.value)} onBlur={() => setNumInput(String(clampCount(numInput)))} className="w-32" />
            {type === "hr" && clampCount(numInput) > 10 && <p className="mt-1 text-xs text-ink-faint">The built-in HR bank has 10 questions; beyond that the app generates more (with a live AI model they are fresh and tailored).</p>}
          </div>
          {type === "technical" && (
            <div>
              <Label htmlFor="topic">Topic</Label>
              <Select id="topic" value={topic} onChange={(e) => setTopic(e.target.value)}>
                {TOPICS.map((t) => <option key={t} value={t}>{TOPIC_NAMES[t] || titleCase(t)}</option>)}
              </Select>
              {topic === "mixed" && <p className="mt-1 text-xs text-ink-faint">Mixed rotates topics, starting with your weakest ones and the skills on your resume.</p>}
            </div>
          )}
          <label className="flex items-center justify-between gap-4 rounded-card border border-paper-line p-3">
            <span><span className="block text-sm font-medium">Adaptive difficulty</span><span className="text-xs text-ink-faint">Harder after strong answers, easier after weak ones, with follow-ups on gaps.</span></span>
            <Switch checked={adaptive} onCheckedChange={setAdaptive} aria-label="Adaptive difficulty" />
          </label>
          <label className="flex items-center justify-between gap-4 rounded-card border border-paper-line p-3">
            <span><span className="block text-sm font-medium">Voice interview</span><span className="text-xs text-ink-faint">Questions are read aloud; answer by speaking. You get pace, filler-word and pause feedback.{!speech.supported && " (Your browser has no speech input; you can still type.)"}</span></span>
            <Switch checked={voiceMode} onCheckedChange={setVoiceMode} aria-label="Voice interview" />
          </label>
          <Button variant="accent" onClick={handleStart} disabled={loading} size="lg">{loading ? "Starting..." : "Start interview"}</Button>
        </CardContent></Card>
      </div>
    );
  }

  if (phase === "complete" && summary) {
    const strengths: string[] = summary.strengths || [];
    const weaknesses: string[] = summary.weaknesses || [];
    const topics: string[] = summary.recommended_topics || [];
    return (
      <div className="max-w-3xl">
        <PageHeader title="Interview completed" description={`${title} - ${fmt(elapsed)} elapsed`} />
        {answeredAny === 0 ? (
          <Card className="p-6 text-sm">{summary.ai_feedback}</Card>
        ) : (
          <>
            <Card className="mb-4 grid gap-6 p-6 sm:grid-cols-3">
              <ScoreRing value={summary.overall_score} label={String(Math.round(summary.overall_score))} sublabel="Overall score" />
              <ScoreRing value={summary.technical_score ?? 0} label={String(Math.round(summary.technical_score ?? 0))} sublabel="Technical" />
              <ScoreRing value={summary.communication_score ?? 0} label={String(Math.round(summary.communication_score ?? 0))} sublabel="Communication" />
            </Card>
            <Card className="mb-4"><CardHeader><CardTitle>AI Feedback</CardTitle></CardHeader><CardContent><p className="text-sm">{summary.ai_feedback}</p></CardContent></Card>
            <div className="mb-4 grid gap-4 md:grid-cols-2">
              <Card><CardHeader><CardTitle>Strengths</CardTitle></CardHeader><CardContent><ul className="list-disc space-y-1 pl-5 text-sm">{strengths.length ? strengths.map((s) => <li key={s}>{s}</li>) : <li className="list-none text-ink-faint">None stood out yet.</li>}</ul></CardContent></Card>
              <Card><CardHeader><CardTitle>Weaknesses</CardTitle></CardHeader><CardContent><ul className="list-disc space-y-1 pl-5 text-sm">{weaknesses.length ? weaknesses.map((s) => <li key={s}>{s}</li>) : <li className="list-none text-ink-faint">No major weaknesses.</li>}</ul></CardContent></Card>
            </div>
            {topics.length > 0 && <Card className="mb-4 p-5"><p className="mb-2 text-sm font-medium">Recommended topics</p><div className="flex flex-wrap gap-2">{topics.map((t) => <Badge key={t} tone="amber">{titleCase(t)}</Badge>)}</div></Card>}
          </>
        )}
        <div className="flex flex-wrap gap-3">
          <Button asChild variant="accent"><Link to={`/history/${interview.interview_id}`}>Detailed answers and ideal answers</Link></Button>
          <Button variant="outline" onClick={() => navigate("/dashboard")}>Back to dashboard</Button>
        </div>
      </div>
    );
  }

  const isLastMain = !current?.is_followup && answeredMain + 1 >= interview.target_questions;
  return (
    <div className="max-w-3xl">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium">{current.is_followup ? "Follow-up question" : `Question ${Math.min(answeredMain + 1, interview.target_questions)} of ${interview.target_questions}`}</span>
          <Badge tone={DIFF_TONE[current.difficulty] || "neutral"}>{current.difficulty}</Badge>
          <Badge>{titleCase(current.skill_tag)}</Badge>
          {interview.adaptive && <Badge tone="teal">adaptive</Badge>}
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 font-mono text-sm text-ink-faint"><Clock size={14} /> {fmt(elapsed)}</span>
          <Button variant="ghost" size="sm" onClick={handleEndEarly} disabled={loading}><Flag size={14} /> End early</Button>
        </div>
      </div>

      <Card className="mb-4 p-6">
        <div className="flex items-start justify-between gap-3">
          <p className="font-display text-xl leading-snug">{current.question_text}</p>
          <Button variant="outline" size="icon" aria-label="Read question aloud" onClick={() => speak(current.question_text)}><Volume2 size={16} /></Button>
        </div>
      </Card>

      {!feedback ? (
        <Card className="p-5">
          <Textarea aria-label="Your answer" rows={7} placeholder="Type your answer, or use the microphone..." value={answerText}
            onChange={(e) => { setAnswerText(e.target.value); if (inputMode === "voice") setInputMode("text"); }} disabled={loading} />
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              {speech.supported && (
                <Button variant={speech.listening ? "danger" : "outline"} onClick={() => (speech.listening ? speech.stop() : speech.start())} disabled={speech.transcribing}>
                  {speech.listening ? <><MicOff size={15} /> Stop</> : <><Mic size={15} /> {speech.transcribing ? "Transcribing..." : "Speak"}</>}
                </Button>
              )}
              {speech.listening && <span className="text-xs text-clay" role="status">Listening...</span>}
            </div>
            <Button variant="accent" onClick={handleSubmit} disabled={loading}>{loading ? "Evaluating..." : <><Send size={15} /> Submit answer</>}</Button>
          </div>
        </Card>
      ) : (
        <Card className="p-5" aria-live="polite">
          <div className="mb-3 flex items-center justify-between"><p className="font-medium">Feedback on this answer</p><span className="font-mono text-2xl">{Math.round(feedback.score)}<span className="text-sm text-ink-faint">/100</span></span></div>
          <SimulatedNote simulated={feedback.simulated} />
          <p className="my-3 text-sm">{feedback.feedback}</p>
          <RubricBars rubric={feedback.rubric} />
          {feedback.missing_points?.length > 0 && <p className="mt-3 text-sm"><span className="font-medium">Missed: </span>{feedback.missing_points.join(", ")}</p>}
          {feedback.ideal_answer && <details className="mt-3 text-sm"><summary className="cursor-pointer font-medium">Ideal answer</summary><p className="mt-1 text-ink-soft">{feedback.ideal_answer}</p></details>}
          {feedback.speech && (
            <div className="mt-3 rounded-card bg-paper p-3 text-sm">
              <p className="mb-1 font-medium">Voice delivery</p>
              <p className="font-mono text-xs text-ink-faint">{feedback.speech.wpm ?? "-"} words/min · {feedback.speech.filler_total} filler words · {feedback.speech.long_pauses} long pauses</p>
              <ul className="mt-1 list-disc pl-5">{feedback.speech.feedback.map((f: string) => <li key={f}>{f}</li>)}</ul>
            </div>
          )}
          <div className="mt-4 text-right"><Button variant="accent" onClick={handleNext} disabled={loading}>{pendingNext ? <>Next question <ArrowRight size={15} /></> : "Finish and see results"}</Button></div>
        </Card>
      )}
      {loading && !feedback && <Spinner label="Evaluating your answer..." />}
    </div>
  );
}
