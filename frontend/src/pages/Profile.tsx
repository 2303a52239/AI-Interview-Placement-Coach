import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Trash2, UploadCloud, Wand2, Camera } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { updateProfile, getMe, getReadiness, autofillProfile, uploadPhoto, deletePhoto, fetchPhotoBlob, getResume, uploadResume, listRoles, getErrorMessage } from "../services/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input, Textarea, Select, Label } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { PageHeader, PageSkeleton } from "@/components/ui/page";
import { titleCase } from "@/lib/utils";

const PROFICIENCY = ["beginner", "intermediate", "advanced", "expert"];
const COMPANIES = ["Microsoft", "Google", "Amazon", "Accenture", "Infosys", "TCS", "Deloitte"];
const FALLBACK_ROLES = ["Software Developer", "Java Developer", "Python Developer", "Full Stack Developer", "Data Analyst", "Data Scientist", "Machine Learning Engineer"];

type Form = Record<string, any>;
const EMPTY: Form = {
  name: "", college: "", degree: "", branch: "", graduation_year: "", cgpa: "", phone: "", location: "",
  target_role: "Software Developer", experience_years: "0", github_url: "", linkedin_url: "", leetcode_url: "", portfolio_url: "",
  career_objective: "", preferred_companies: [], target_roles: [], skills: [], projects: [], certifications: [], internships: [],
};

function Field({ id, label, children }: { id: string; label: string; children: React.ReactNode }) {
  return <div><Label htmlFor={id}>{label}</Label>{children}</div>;
}

export default function Profile() {
  const { user, refreshUser } = useAuth();
  const { showToast } = useToast();
  const [form, setForm] = useState<Form>(EMPTY);
  const [loaded, setLoaded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [readiness, setReadiness] = useState<any>(null);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const [resumeName, setResumeName] = useState<string | null>(null);
  const [roles, setRoles] = useState<string[]>(FALLBACK_ROLES);
  const [busy, setBusy] = useState("");
  const photoRef = useRef<HTMLInputElement>(null);
  const resumeRef = useRef<HTMLInputElement>(null);

  const set = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));
  const setItem = (k: string, i: number, patch: Form) => setForm((f) => ({ ...f, [k]: f[k].map((x: Form, j: number) => (j === i ? { ...x, ...patch } : x)) }));
  const addItem = (k: string, item: Form) => setForm((f) => ({ ...f, [k]: [...f[k], item] }));
  const delItem = (k: string, i: number) => setForm((f) => ({ ...f, [k]: f[k].filter((_: any, j: number) => j !== i) }));
  const toggle = (k: string, v: string) => setForm((f) => ({ ...f, [k]: f[k].includes(v) ? f[k].filter((x: string) => x !== v) : [...f[k], v] }));

  const applyProfile = (u: any) => {
    const p = u.profile || {};
    setForm({
      ...EMPTY, ...p, name: u.name ?? "", graduation_year: p.graduation_year ?? "", cgpa: p.cgpa ?? "",
      skills: p.skills || [], projects: p.projects || [], certifications: p.certifications || [], internships: p.internships || [],
      preferred_companies: p.preferred_companies || [], target_roles: p.target_roles || [],
    });
  };
  const loadPhoto = async () => {
    try { const r = await fetchPhotoBlob(); setPhotoUrl((old) => { if (old) URL.revokeObjectURL(old); return URL.createObjectURL(r.data); }); } catch { setPhotoUrl(null); }
  };
  const loadReadiness = () => getReadiness().then((r) => setReadiness(r.data)).catch(() => undefined);

  useEffect(() => {
    getMe().then((r) => { applyProfile(r.data); setLoaded(true); if (r.data.profile?.has_photo) loadPhoto(); }).catch((e) => { showToast(getErrorMessage(e, "Could not load your profile."), "error"); setLoaded(true); });
    getResume().then((r) => setResumeName(r.data.original_filename)).catch(() => setResumeName(null));
    listRoles().then((r) => { const names = (r.data.roles || r.data || []).map((x: any) => (typeof x === "string" ? x : x.name)); if (names.length) setRoles(names); }).catch(() => undefined);
    loadReadiness();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const save = async () => {
    if (form.cgpa !== "" && (Number(form.cgpa) < 0 || Number(form.cgpa) > 10)) { showToast("CGPA must be between 0 and 10.", "error"); return; }
    setSaving(true);
    try {
      const payload: Form = { ...form, graduation_year: form.graduation_year === "" ? null : Number(form.graduation_year), cgpa: form.cgpa === "" ? null : Number(form.cgpa) };
      delete payload.has_photo; delete payload.skills_text; delete payload.projects_text;
      payload.certifications = form.certifications.map((c: Form) => ({ ...c, year: c.year === "" || c.year == null ? null : Number(c.year) }));
      await updateProfile(payload);
      await refreshUser(); await loadReadiness();
      showToast("Profile saved.", "success");
    } catch (e) { showToast(getErrorMessage(e, "Could not save your profile."), "error"); } finally { setSaving(false); }
  };

  const onPhoto = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]; e.target.value = "";
    if (!f) return;
    setBusy("photo");
    try { await uploadPhoto(f); await loadPhoto(); showToast("Photo updated.", "success"); } catch (err) { showToast(getErrorMessage(err, "Could not upload the photo."), "error"); } finally { setBusy(""); }
  };
  const removePhoto = async () => { try { await deletePhoto(); setPhotoUrl(null); showToast("Photo removed.", "success"); } catch (err) { showToast(getErrorMessage(err), "error"); } };

  const onResume = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]; e.target.value = "";
    if (!f) return;
    setBusy("resume");
    try { const r = await uploadResume(f); setResumeName(r.data.original_filename); showToast("Resume uploaded. Use auto-fill to copy its details into your profile.", "success"); loadReadiness(); } catch (err) { showToast(getErrorMessage(err, "Could not process this resume."), "error"); } finally { setBusy(""); }
  };
  const autofill = async () => {
    setBusy("autofill");
    try {
      const r = await autofillProfile(false);
      applyProfile({ name: form.name, profile: r.data.profile });
      const n = (r.data.updated_fields || []).length;
      showToast(n ? `Filled from your resume: ${r.data.updated_fields.join(", ")}. Existing entries were kept.` : "Nothing new to fill: your profile already has these details.", "success");
      loadReadiness();
    } catch (err) { showToast(getErrorMessage(err, "Upload a resume first."), "error"); } finally { setBusy(""); }
  };

  if (!loaded) return <PageSkeleton />;
  const init = (user?.name || "?").slice(0, 1).toUpperCase();

  return (
    <div className="max-w-4xl">
      <PageHeader title="Your profile" description="Interviews, the skill-gap analysis and your roadmap are built from what you enter here." actions={<Button variant="accent" onClick={save} disabled={saving}>{saving ? "Saving..." : "Save profile"}</Button>} />

      <Card className="mb-5 p-5">
        <div className="flex flex-wrap items-center gap-5">
          <div className="relative">
            {photoUrl ? <img src={photoUrl} alt="Profile" className="h-20 w-20 rounded-full object-cover" /> : <div className="flex h-20 w-20 items-center justify-center rounded-full bg-teal-light font-display text-2xl text-teal-dark" aria-label="No photo">{init}</div>}
            <button type="button" aria-label="Change photo" onClick={() => photoRef.current?.click()} className="absolute -bottom-1 -right-1 rounded-full border border-paper-line bg-paper-panel p-1.5"><Camera size={14} /></button>
            <input ref={photoRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" aria-label="Upload photo" onChange={onPhoto} />
          </div>
          <div className="min-w-[200px] flex-1">
            <p className="font-medium">{user?.name}</p>
            <p className="text-sm text-ink-faint">{user?.email}</p>
            {photoUrl && <button className="mt-1 text-xs text-clay underline" onClick={removePhoto}>Remove photo</button>}
            {busy === "photo" && <span className="ml-2 text-xs text-ink-faint">Uploading...</span>}
          </div>
          {readiness && (
            <div className="w-full sm:w-64">
              <div className="mb-1 flex justify-between text-sm"><span>Placement readiness</span><span className="font-mono">{Math.round(readiness.score)}</span></div>
              <Progress value={readiness.score} tone={readiness.score >= 75 ? "teal" : readiness.score >= 55 ? "amber" : "clay"} aria-label="Placement readiness" />
              <p className="mt-1 text-xs text-ink-faint">{readiness.band}{readiness.profile_gaps?.length ? ` · missing: ${readiness.profile_gaps.slice(0, 3).join(", ")}` : ""}</p>
            </div>
          )}
        </div>
      </Card>

      <Tabs defaultValue="basics">
        <TabsList className="mb-4 flex-wrap"><TabsTrigger value="basics">Basics</TabsTrigger><TabsTrigger value="skills">Skills</TabsTrigger><TabsTrigger value="experience">Projects &amp; experience</TabsTrigger><TabsTrigger value="goals">Links &amp; goals</TabsTrigger><TabsTrigger value="resume">Resume</TabsTrigger></TabsList>

        <TabsContent value="basics"><Card><CardContent className="grid gap-4 pt-5 sm:grid-cols-2">
          <Field id="name" label="Full name"><Input id="name" value={form.name} onChange={(e) => set("name", e.target.value)} /></Field>
          <Field id="phone" label="Phone"><Input id="phone" value={form.phone} onChange={(e) => set("phone", e.target.value)} /></Field>
          <Field id="college" label="University / college"><Input id="college" value={form.college} onChange={(e) => set("college", e.target.value)} /></Field>
          <Field id="degree" label="Degree"><Input id="degree" value={form.degree} onChange={(e) => set("degree", e.target.value)} placeholder="B.Tech" /></Field>
          <Field id="branch" label="Branch"><Input id="branch" value={form.branch} onChange={(e) => set("branch", e.target.value)} placeholder="Computer Science" /></Field>
          <Field id="gradyear" label="Graduation year"><Input id="gradyear" type="number" min={1990} max={2100} value={form.graduation_year} onChange={(e) => set("graduation_year", e.target.value)} /></Field>
          <Field id="cgpa" label="CGPA (0-10)"><Input id="cgpa" type="number" step="0.01" min={0} max={10} value={form.cgpa} onChange={(e) => set("cgpa", e.target.value)} /></Field>
          <Field id="location" label="Location"><Input id="location" value={form.location} onChange={(e) => set("location", e.target.value)} /></Field>
          <Field id="exp" label="Experience"><Select id="exp" value={form.experience_years} onChange={(e) => set("experience_years", e.target.value)}>{["0", "0-1", "1-2", "2-3", "3+"].map((x) => <option key={x} value={x}>{x === "0" ? "Fresher" : `${x} years`}</option>)}</Select></Field>
        </CardContent></Card></TabsContent>

        <TabsContent value="skills"><Card><CardHeader><CardTitle>Skills and proficiency</CardTitle><CardDescription>Be honest: proficiency feeds interview difficulty and the skill-gap analysis.</CardDescription></CardHeader><CardContent className="space-y-2">
          {form.skills.map((s: Form, i: number) => (
            <div key={i} className="flex gap-2">
              <Input aria-label={`Skill ${i + 1} name`} value={s.name} onChange={(e) => setItem("skills", i, { name: e.target.value })} placeholder="e.g. Python" />
              <Select aria-label={`Skill ${i + 1} proficiency`} className="w-40" value={s.proficiency} onChange={(e) => setItem("skills", i, { proficiency: e.target.value })}>{PROFICIENCY.map((p) => <option key={p} value={p}>{titleCase(p)}</option>)}</Select>
              <Button variant="ghost" size="icon" aria-label={`Remove skill ${i + 1}`} onClick={() => delItem("skills", i)}><Trash2 size={15} /></Button>
            </div>
          ))}
          <Button variant="outline" size="sm" onClick={() => addItem("skills", { name: "", proficiency: "intermediate" })}><Plus size={14} /> Add skill</Button>
        </CardContent></Card></TabsContent>

        <TabsContent value="experience" className="space-y-5">
          <Card><CardHeader><CardTitle>Projects</CardTitle></CardHeader><CardContent className="space-y-4">
            {form.projects.map((p: Form, i: number) => (
              <div key={i} className="space-y-2 rounded-card border border-paper-line p-3">
                <div className="flex gap-2"><Input aria-label={`Project ${i + 1} title`} placeholder="Title" value={p.title} onChange={(e) => setItem("projects", i, { title: e.target.value })} /><Button variant="ghost" size="icon" aria-label={`Remove project ${i + 1}`} onClick={() => delItem("projects", i)}><Trash2 size={15} /></Button></div>
                <Textarea aria-label={`Project ${i + 1} description`} rows={2} placeholder="What it does and what you built" value={p.description} onChange={(e) => setItem("projects", i, { description: e.target.value })} />
                <div className="grid gap-2 sm:grid-cols-2"><Input aria-label={`Project ${i + 1} technologies`} placeholder="Technologies" value={p.technologies} onChange={(e) => setItem("projects", i, { technologies: e.target.value })} /><Input aria-label={`Project ${i + 1} GitHub URL`} placeholder="https://github.com/..." value={p.github_url} onChange={(e) => setItem("projects", i, { github_url: e.target.value })} /></div>
              </div>
            ))}
            <Button variant="outline" size="sm" onClick={() => addItem("projects", { title: "", description: "", technologies: "", github_url: "" })}><Plus size={14} /> Add project</Button>
          </CardContent></Card>
          <Card><CardHeader><CardTitle>Internships</CardTitle></CardHeader><CardContent className="space-y-4">
            {form.internships.map((p: Form, i: number) => (
              <div key={i} className="space-y-2 rounded-card border border-paper-line p-3">
                <div className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]"><Input aria-label={`Internship ${i + 1} company`} placeholder="Company" value={p.company} onChange={(e) => setItem("internships", i, { company: e.target.value })} /><Input aria-label={`Internship ${i + 1} role`} placeholder="Role" value={p.role} onChange={(e) => setItem("internships", i, { role: e.target.value })} /><Button variant="ghost" size="icon" aria-label={`Remove internship ${i + 1}`} onClick={() => delItem("internships", i)}><Trash2 size={15} /></Button></div>
                <div className="grid gap-2 sm:grid-cols-2"><Input aria-label={`Internship ${i + 1} start`} placeholder="Start (e.g. 2025-05)" value={p.start_date} onChange={(e) => setItem("internships", i, { start_date: e.target.value })} /><Input aria-label={`Internship ${i + 1} end`} placeholder="End" value={p.end_date} onChange={(e) => setItem("internships", i, { end_date: e.target.value })} /></div>
                <Textarea aria-label={`Internship ${i + 1} description`} rows={2} placeholder="What you worked on" value={p.description} onChange={(e) => setItem("internships", i, { description: e.target.value })} />
              </div>
            ))}
            <Button variant="outline" size="sm" onClick={() => addItem("internships", { company: "", role: "", start_date: "", end_date: "", description: "" })}><Plus size={14} /> Add internship</Button>
          </CardContent></Card>
          <Card><CardHeader><CardTitle>Certifications</CardTitle></CardHeader><CardContent className="space-y-2">
            {form.certifications.map((p: Form, i: number) => (
              <div key={i} className="grid gap-2 sm:grid-cols-[2fr_1.5fr_90px_auto]">
                <Input aria-label={`Certification ${i + 1} name`} placeholder="Name" value={p.name} onChange={(e) => setItem("certifications", i, { name: e.target.value })} />
                <Input aria-label={`Certification ${i + 1} issuer`} placeholder="Issuer" value={p.issuer} onChange={(e) => setItem("certifications", i, { issuer: e.target.value })} />
                <Input aria-label={`Certification ${i + 1} year`} type="number" placeholder="Year" value={p.year ?? ""} onChange={(e) => setItem("certifications", i, { year: e.target.value })} />
                <Button variant="ghost" size="icon" aria-label={`Remove certification ${i + 1}`} onClick={() => delItem("certifications", i)}><Trash2 size={15} /></Button>
              </div>
            ))}
            <Button variant="outline" size="sm" onClick={() => addItem("certifications", { name: "", issuer: "", year: "", url: "" })}><Plus size={14} /> Add certification</Button>
          </CardContent></Card>
        </TabsContent>

        <TabsContent value="goals"><Card><CardContent className="space-y-4 pt-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field id="gh" label="GitHub"><Input id="gh" value={form.github_url} onChange={(e) => set("github_url", e.target.value)} placeholder="https://github.com/you" /></Field>
            <Field id="li" label="LinkedIn"><Input id="li" value={form.linkedin_url} onChange={(e) => set("linkedin_url", e.target.value)} /></Field>
            <Field id="lc" label="LeetCode"><Input id="lc" value={form.leetcode_url} onChange={(e) => set("leetcode_url", e.target.value)} /></Field>
            <Field id="pf" label="Portfolio"><Input id="pf" value={form.portfolio_url} onChange={(e) => set("portfolio_url", e.target.value)} /></Field>
          </div>
          <Field id="obj" label="Career objective"><Textarea id="obj" rows={3} value={form.career_objective} onChange={(e) => set("career_objective", e.target.value)} /></Field>
          <Field id="primary" label="Primary target role"><Select id="primary" value={form.target_role} onChange={(e) => set("target_role", e.target.value)}>{[...new Set([form.target_role, ...roles])].filter(Boolean).map((r) => <option key={r}>{r}</option>)}</Select></Field>
          <div><p className="mb-1 text-sm font-medium">Other target roles</p><div className="flex flex-wrap gap-2">{roles.map((r) => <button key={r} type="button" aria-pressed={form.target_roles.includes(r)} onClick={() => toggle("target_roles", r)}><Badge tone={form.target_roles.includes(r) ? "teal" : "neutral"}>{r}</Badge></button>)}</div></div>
          <div><p className="mb-1 text-sm font-medium">Preferred companies</p><div className="flex flex-wrap gap-2">{COMPANIES.map((r) => <button key={r} type="button" aria-pressed={form.preferred_companies.includes(r)} onClick={() => toggle("preferred_companies", r)}><Badge tone={form.preferred_companies.includes(r) ? "teal" : "neutral"}>{r}</Badge></button>)}</div></div>
        </CardContent></Card></TabsContent>

        <TabsContent value="resume"><Card><CardContent className="space-y-4 pt-5">
          <p className="text-sm">{resumeName ? <>Active resume: <span className="font-medium">{resumeName}</span>. <Link to="/resume" className="text-teal underline">View analysis and versions</Link></> : "No resume uploaded yet."}</p>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => resumeRef.current?.click()} disabled={busy === "resume"}><UploadCloud size={15} /> {busy === "resume" ? "Uploading..." : "Upload resume (PDF or DOCX)"}</Button>
            <input ref={resumeRef} type="file" accept=".pdf,.docx" className="hidden" aria-label="Upload resume file" onChange={onResume} />
            <Button variant="accent" onClick={autofill} disabled={!resumeName || busy === "autofill"}><Wand2 size={15} /> {busy === "autofill" ? "Filling..." : "Auto-fill profile from resume"}</Button>
          </div>
          <p className="text-xs text-ink-faint">Auto-fill only adds what is missing; anything you already entered is kept. Skill proficiency can't be read from a resume, so new skills start at Intermediate: adjust them on the Skills tab, then save.</p>
        </CardContent></Card></TabsContent>
      </Tabs>
    </div>
  );
}
