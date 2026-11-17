import { useEffect, useRef, useState } from "react";
import { UploadCloud, CheckCircle2, XCircle, Trash2 } from "lucide-react";
import { uploadResume, getResume, getResumeById, listResumeVersions, activateResume, deleteResume, listJobDescriptions, matchResume, listMatches, getErrorMessage } from "../services/api";
import { useToast } from "../context/ToastContext";
import { useConfirm } from "../context/ConfirmContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input, Textarea, Select, Label } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { ScoreRing } from "@/components/ui/ScoreRing";
import { PageHeader, PageSkeleton, Empty } from "@/components/ui/page";
import { titleCase } from "@/lib/utils";

function Chips({ title, items }: { title: string; items?: string[] }) {
  if (!items?.length) return null;
  return <div className="mb-4"><p className="mb-1.5 font-mono text-xs uppercase tracking-wide text-ink-faint">{title}</p><div className="flex flex-wrap gap-2">{items.map((i) => <Badge key={i}>{i}</Badge>)}</div></div>;
}

export default function Resume() {
  const { showToast } = useToast();
  const confirm = useConfirm();
  const [resume, setResume] = useState<any>(null);
  const [versions, setVersions] = useState<any[]>([]);
  const [jds, setJds] = useState<any[]>([]);
  const [matches, setMatches] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [label, setLabel] = useState("");
  const [jdId, setJdId] = useState("");
  const [jdText, setJdText] = useState("");
  const [jdTitle, setJdTitle] = useState("");
  const [match, setMatch] = useState<any>(null);
  const [matching, setMatching] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const loadAll = async () => {
    const [cur, vs, js, ms] = await Promise.all([
      getResume().then((r) => r.data).catch(() => null), listResumeVersions().then((r) => r.data).catch(() => []),
      listJobDescriptions().then((r) => r.data).catch(() => []), listMatches().then((r) => r.data).catch(() => []),
    ]);
    setResume(cur); setVersions(vs); setJds(js); setMatches(ms);
  };
  useEffect(() => { loadAll().finally(() => setLoading(false)); }, []);

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]; e.target.value = "";
    if (!f) return;
    setUploading(true);
    try { const r = await uploadResume(f, label); setLabel(""); setMatch(null); await loadAll(); showToast(`Uploaded as version ${r.data.version}.`, "success"); }
    catch (err) { showToast(getErrorMessage(err, "Could not process this resume."), "error"); } finally { setUploading(false); }
  };
  const activate = async (id: number) => { try { await activateResume(id); await loadAll(); showToast("Active resume changed.", "success"); } catch (e) { showToast(getErrorMessage(e), "error"); } };
  const view = async (id: number) => { try { setResume((await getResumeById(id)).data); } catch (e) { showToast(getErrorMessage(e), "error"); } };
  const remove = async (v: any) => {
    if (!(await confirm({ title: `Delete version ${v.version}?`, message: `${v.original_filename} will be permanently removed.`, confirmLabel: "Delete" }))) return;
    try { await deleteResume(v.id); await loadAll(); } catch (e) { showToast(getErrorMessage(e), "error"); }
  };
  const runMatch = async () => {
    if (!jdId && jdText.trim().length < 20) { showToast("Pick a saved job description or paste at least a few sentences.", "error"); return; }
    setMatching(true);
    try { const r = await matchResume({ resume_id: resume?.id, jd_id: jdId ? Number(jdId) : undefined, jd_text: jdId ? undefined : jdText, jd_title: jdTitle }); setMatch(r.data); listMatches().then((x) => setMatches(x.data)); }
    catch (e) { showToast(getErrorMessage(e, "Could not match against that description."), "error"); } finally { setMatching(false); }
  };

  if (loading) return <PageSkeleton />;
  const a = resume?.analysis || {};
  const ats = a.ats, quality = a.quality;

  return (
    <div className="max-w-5xl">
      <PageHeader title="Resume intelligence" description="Upload a PDF or DOCX. Skills, projects and education are extracted with a fixed skills dictionary and pattern rules (not a language model), then scored for ATS readability and quality."
        actions={<>
          <Input aria-label="Version label" className="w-44" placeholder="Label (optional)" value={label} onChange={(e) => setLabel(e.target.value)} />
          <Button variant="accent" onClick={() => fileRef.current?.click()} disabled={uploading}><UploadCloud size={15} /> {uploading ? "Analysing..." : "Upload resume"}</Button>
          <input ref={fileRef} type="file" accept=".pdf,.docx" className="hidden" aria-label="Upload resume file" onChange={onFile} />
        </>} />
      {!resume ? <Empty title="No resume yet" description="Upload your resume (PDF or DOCX, up to 5 MB) to get skills extraction, an ATS check and personalised interview questions." /> : (
        <Tabs defaultValue="overview">
          <TabsList className="mb-4 flex-wrap"><TabsTrigger value="overview">Overview</TabsTrigger><TabsTrigger value="ats">ATS &amp; quality</TabsTrigger><TabsTrigger value="match">Job match</TabsTrigger><TabsTrigger value="versions">Versions ({versions.length})</TabsTrigger></TabsList>

          <TabsContent value="overview" className="space-y-4">
            <Card className="flex flex-wrap items-center gap-6 p-5">
              <ScoreRing value={resume.ats_score ?? 0} label={resume.ats_score != null ? String(Math.round(resume.ats_score)) : "-"} sublabel="ATS score" />
              <ScoreRing value={resume.quality_score ?? 0} label={resume.quality_score != null ? String(Math.round(resume.quality_score)) : "-"} sublabel="Quality" />
              <div className="text-sm"><p className="font-medium">{resume.original_filename}</p><p className="text-ink-faint">Version {resume.version}{resume.label ? ` · ${resume.label}` : ""}{resume.is_active ? " · active" : ""}</p></div>
            </Card>
            <Card><CardContent className="pt-5">
              {a.skills_by_category && Object.entries(a.skills_by_category).map(([cat, items]) => <Chips key={cat} title={titleCase(cat)} items={items as string[]} />)}
              <Chips title="Projects" items={resume.extracted_projects} /><Chips title="Education" items={resume.extracted_education} /><Chips title="Experience" items={resume.extracted_experience} /><Chips title="Certifications" items={resume.extracted_certifications} />
              {!resume.extracted_skills?.length && <p className="text-sm text-ink-faint">No known skills were detected. Add a clear "Skills" section listing technologies by name.</p>}
            </CardContent></Card>
            {a.suggestions?.length > 0 && <Card><CardHeader><CardTitle>Suggestions</CardTitle></CardHeader><CardContent><ul className="list-disc space-y-1 pl-5 text-sm">{a.suggestions.map((s: string) => <li key={s}>{s}</li>)}</ul></CardContent></Card>}
          </TabsContent>

          <TabsContent value="ats" className="grid gap-4 md:grid-cols-2">
            <Card><CardHeader><CardTitle>ATS checks</CardTitle><CardDescription>Score {ats ? Math.round(ats.score) : "-"} / 100</CardDescription></CardHeader><CardContent className="space-y-2">
              {ats?.checks.map((c: any) => <div key={c.check} className="flex gap-2 text-sm">{c.passed ? <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-teal" /> : <XCircle size={16} className="mt-0.5 shrink-0 text-clay" />}<div><p className="font-medium">{c.check} <span className="font-mono text-xs text-ink-faint">({c.weight})</span></p><p className="text-xs text-ink-faint">{c.detail}</p></div></div>)}
            </CardContent></Card>
            <Card><CardHeader><CardTitle>Quality dimensions</CardTitle><CardDescription>Score {quality ? Math.round(quality.score) : "-"} / 100</CardDescription></CardHeader><CardContent className="space-y-3">
              {quality && Object.entries(quality.dimensions).map(([k, v]: any) => <div key={k}><div className="flex justify-between text-sm"><span>{titleCase(k)}</span><span className="font-mono">{Math.round(v.score)}</span></div><Progress value={v.score} tone={v.score >= 70 ? "teal" : v.score >= 45 ? "amber" : "clay"} aria-label={titleCase(k)} /><p className="text-xs text-ink-faint">{v.meaning}</p></div>)}
            </CardContent></Card>
          </TabsContent>

          <TabsContent value="match" className="space-y-4">
            <Card><CardHeader><CardTitle>Match against a job description</CardTitle><CardDescription>Skill coverage (80%) plus keyword similarity (20%). It measures wording overlap, not hiring odds.</CardDescription></CardHeader><CardContent className="space-y-3">
              <div><Label htmlFor="jd">Saved job description</Label><Select id="jd" value={jdId} onChange={(e) => setJdId(e.target.value)}><option value="">Paste my own</option>{jds.map((j) => <option key={j.id} value={j.id}>{j.title}{j.company ? ` - ${j.company}` : ""}</option>)}</Select></div>
              {!jdId && <><div><Label htmlFor="jdt">Title (optional)</Label><Input id="jdt" value={jdTitle} onChange={(e) => setJdTitle(e.target.value)} /></div><div><Label htmlFor="jdx">Job description text</Label><Textarea id="jdx" rows={6} value={jdText} onChange={(e) => setJdText(e.target.value)} placeholder="Paste the job description here" /></div></>}
              <Button variant="accent" onClick={runMatch} disabled={matching}>{matching ? "Matching..." : "Match resume"}</Button>
            </CardContent></Card>
            {match && <Card className="p-5" aria-live="polite"><div className="mb-3 flex items-center gap-4"><ScoreRing value={match.match_score} label={String(Math.round(match.match_score))} sublabel="Match" /><div><p className="font-medium">{match.jd_title || "Pasted description"}</p></div></div>
              <Chips title="Matched skills" items={match.matched_skills} /><Chips title="Missing skills" items={match.missing_skills} />
              {match.suggestions?.length > 0 && <ul className="list-disc space-y-1 pl-5 text-sm">{match.suggestions.map((s: string) => <li key={s}>{s}</li>)}</ul>}</Card>}
            {matches.length > 0 && <Card><CardHeader><CardTitle>Previous matches</CardTitle></CardHeader><CardContent className="divide-y divide-paper-line">{matches.slice(0, 8).map((m) => <div key={m.id} className="flex justify-between py-2 text-sm"><span>{m.jd_title || "Pasted description"}</span><span className="font-mono">{Math.round(m.match_score)}%</span></div>)}</CardContent></Card>}
          </TabsContent>

          <TabsContent value="versions"><Card><CardContent className="divide-y divide-paper-line pt-3">
            {versions.map((v) => <div key={v.id} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
              <div><p className="font-medium">v{v.version} · {v.original_filename} {v.is_active && <Badge tone="teal">active</Badge>}</p><p className="text-xs text-ink-faint">{v.label || "no label"} · ATS {v.ats_score != null ? Math.round(v.ats_score) : "-"} · quality {v.quality_score != null ? Math.round(v.quality_score) : "-"} · {new Date(v.uploaded_at).toLocaleDateString()}</p></div>
              <div className="flex gap-2"><Button size="sm" variant="outline" onClick={() => view(v.id)}>View</Button>{!v.is_active && <Button size="sm" variant="outline" onClick={() => activate(v.id)}>Make active</Button>}<Button size="icon" variant="ghost" aria-label={`Delete version ${v.version}`} onClick={() => remove(v)}><Trash2 size={14} /></Button></div></div>)}
          </CardContent></Card></TabsContent>
        </Tabs>
      )}
    </div>
  );
}
