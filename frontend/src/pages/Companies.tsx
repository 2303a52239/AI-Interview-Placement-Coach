import { useEffect, useState } from "react";
import { listCompanies, getCompany, getErrorMessage } from "../services/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Link } from "react-router-dom";
import { PageHeader, PageSkeleton, ErrorBox, Spinner } from "@/components/ui/page";
import { titleCase } from "@/lib/utils";

export default function Companies() {
  const [list, setList] = useState<any[]>([]);
  const [slug, setSlug] = useState("");
  const [guide, setGuide] = useState<any>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [gLoading, setGLoading] = useState(false);

  useEffect(() => { listCompanies().then((r) => { setList(r.data); if (r.data[0]) pick(r.data[0].slug); }).catch((e) => setError(getErrorMessage(e))).finally(() => setLoading(false)); }, []);
  const pick = async (s: string) => {
    setSlug(s); setGLoading(true);
    try { setGuide((await getCompany(s)).data); } catch (e) { setError(getErrorMessage(e)); } finally { setGLoading(false); }
  };

  if (loading) return <PageSkeleton />;
  if (error && !guide) return <ErrorBox message={error} />;
  return (
    <div className="max-w-4xl">
      <PageHeader title="Company preparation" description="General preparation themes per company, matched against your own measured scores." />
      <div className="mb-5 flex flex-wrap gap-2" role="tablist" aria-label="Companies">{list.map((c) => <Button key={c.slug} role="tab" aria-selected={c.slug === slug} size="sm" variant={c.slug === slug ? "accent" : "outline"} onClick={() => pick(c.slug)}>{c.name}</Button>)}</div>
      {gLoading || !guide ? <Spinner /> : (<div className="space-y-4">
        <p className="rounded-card bg-amber-light px-3 py-2 text-xs text-amber-dark">{guide.verify}</p>
        <Card className="p-5"><div className="flex flex-wrap items-center justify-between gap-2"><div><h2 className="font-display text-xl">{guide.name}</h2><Badge>{guide.category}</Badge></div>
          <div className="text-right"><p className="text-xs text-ink-faint">Your readiness for these topics</p><p className="font-mono text-2xl">{guide.readiness === null ? "—" : Math.round(guide.readiness)}</p><p className="text-xs text-ink-faint">{guide.readiness_basis}</p></div></div></Card>
        <div className="grid gap-4 md:grid-cols-2">
          <Card><CardHeader><CardTitle>Preparation themes</CardTitle></CardHeader><CardContent><ul className="list-disc space-y-1 pl-5 text-sm">{guide.themes.map((t: string) => <li key={t}>{t}</li>)}</ul></CardContent></Card>
          <Card><CardHeader><CardTitle>Tips</CardTitle></CardHeader><CardContent><ul className="list-disc space-y-1 pl-5 text-sm">{guide.tips.map((t: string) => <li key={t}>{t}</li>)}</ul></CardContent></Card>
        </div>
        <Card><CardHeader><CardTitle>Focus topics</CardTitle></CardHeader><CardContent className="divide-y divide-paper-line">{guide.focus.map((f: any) => (
          <div key={f.topic} className="flex flex-wrap items-center justify-between gap-2 py-2"><div><p className="font-medium">{titleCase(f.topic)}</p><p className="text-xs text-ink-faint">{f.notes}</p></div>
            <Badge tone={f.status === "strong" ? "teal" : f.status === "needs_work" ? "clay" : "neutral"}>{f.status === "not_attempted" ? "Not attempted" : `${Math.round(f.your_score)} · ${f.status === "strong" ? "strong" : "needs work"}`}</Badge></div>))}</CardContent></Card>
        <div className="flex flex-wrap gap-2"><Button asChild variant="accent"><Link to="/interview/technical">Practise a technical interview</Link></Button><Button asChild variant="outline"><Link to="/coding">Practise coding</Link></Button></div>
      </div>)}
    </div>
  );
}
