import { useEffect, useRef, useState } from "react";
import { Trash2, UploadCloud, FileText, Send, Search } from "lucide-react";
import { ragStatus, ragDocuments, ragUpload, ragIndexResume, ragDelete, ragSearch, ragChat, ragHistory, ragClearHistory, getErrorMessage } from "../services/api";
import { useToast } from "../context/ToastContext";
import { useConfirm } from "../context/ConfirmContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input, Select, Label } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { PageHeader, PageSkeleton, SimulatedNote } from "@/components/ui/page";

type Msg = { role: string; content: string; citations?: any[]; simulated?: boolean };

function Citations({ items }: { items?: any[] }) {
  if (!items?.length) return null;
  return (
    <details className="mt-2 text-xs"><summary className="cursor-pointer text-ink-faint">{items.length} source{items.length > 1 ? "s" : ""}</summary>
      <ol className="mt-1 space-y-1">{items.map((c) => <li key={c.n} className="rounded-card border border-paper-line p-2"><span className="font-medium">[{c.n}] {c.filename}</span> <span className="text-ink-faint">chunk {c.chunk_index}</span><p className="mt-0.5 text-ink-soft">{c.snippet}</p></li>)}</ol></details>
  );
}

export default function Assistant() {
  const { showToast } = useToast();
  const confirm = useConfirm();
  const [status, setStatus] = useState<any>(null);
  const [docs, setDocs] = useState<any[]>([]);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [q, setQ] = useState("");
  const [asking, setAsking] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [docType, setDocType] = useState("notes");
  const [uploading, setUploading] = useState(false);
  const [sq, setSq] = useState("");
  const [mode, setMode] = useState("hybrid");
  const [results, setResults] = useState<any>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  const loadDocs = () => ragDocuments().then((r) => setDocs(r.data));
  useEffect(() => {
    Promise.all([ragStatus().then((r) => setStatus(r.data)), loadDocs(), ragHistory().then((r) => setMsgs(r.data))])
      .catch((e) => showToast(getErrorMessage(e, "Could not load the assistant."), "error")).finally(() => setLoaded(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => { endRef.current?.scrollIntoView?.({ block: "end" }); }, [msgs]);

  const upload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]; e.target.value = "";
    if (!f) return;
    setUploading(true);
    try { const r = await ragUpload(f, docType); await loadDocs(); showToast(`Indexed ${r.data.filename} into ${r.data.chunk_count} chunks.`, "success"); } catch (err) { showToast(getErrorMessage(err, "Could not index that file."), "error"); } finally { setUploading(false); }
  };
  const fromResume = async () => { try { await ragIndexResume(); await loadDocs(); showToast("Resume indexed.", "success"); } catch (err) { showToast(getErrorMessage(err, "Upload a resume first."), "error"); } };
  const remove = async (d: any) => {
    if (!(await confirm({ title: `Delete ${d.filename}?`, message: "Its indexed chunks are removed too.", confirmLabel: "Delete" }))) return;
    try { await ragDelete(d.id); await loadDocs(); } catch (err) { showToast(getErrorMessage(err), "error"); }
  };
  const ask = async (e: React.FormEvent) => {
    e.preventDefault();
    const question = q.trim();
    if (question.length < 2 || asking) return;
    setMsgs((m) => [...m, { role: "user", content: question }]); setQ(""); setAsking(true);
    try { const r = await ragChat({ question }); setMsgs((m) => [...m, { role: "assistant", content: r.data.answer, citations: r.data.citations, simulated: r.data.simulated }]); }
    catch (err) { showToast(getErrorMessage(err, "The assistant could not answer."), "error"); } finally { setAsking(false); }
  };
  const clear = async () => { await ragClearHistory(); setMsgs([]); };
  const search = async (e: React.FormEvent) => {
    e.preventDefault();
    if (sq.trim().length < 2) return;
    try { setResults((await ragSearch({ query: sq, mode, top_k: 6 })).data); } catch (err) { showToast(getErrorMessage(err), "error"); }
  };

  if (!loaded) return <PageSkeleton />;
  return (
    <div className="max-w-5xl">
      <PageHeader title="Study assistant" description="Ask questions about your own notes, resume and job descriptions. Answers cite the passages they came from." />
      {status?.embedding && !status.embedding.semantic && (
        <p className="mb-4 rounded-card bg-amber-light px-3 py-2 text-sm text-amber-dark">{status.embedding.note} Search currently ranks by shared words and phrases.</p>
      )}
      <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
        <Tabs defaultValue="chat">
          <TabsList className="mb-3"><TabsTrigger value="chat">Ask</TabsTrigger><TabsTrigger value="search">Search</TabsTrigger></TabsList>
          <TabsContent value="chat"><Card className="flex flex-col">
            <div className="max-h-[480px] min-h-[280px] flex-1 space-y-3 overflow-y-auto p-4" aria-live="polite">
              {msgs.length === 0 && <p className="py-12 text-center text-sm text-ink-faint">{docs.length ? "Ask something about your documents." : "Upload a document first, then ask questions about it."}</p>}
              {msgs.map((m, i) => (
                <div key={i} className={m.role === "user" ? "ml-10 rounded-card bg-teal-light p-3 text-sm text-teal-dark" : "mr-10 rounded-card border border-paper-line p-3 text-sm"}>
                  <p className="whitespace-pre-wrap">{m.content}</p>{m.role === "assistant" && <><Citations items={m.citations} />{m.simulated && <p className="mt-2 text-xs text-ink-faint">Extractive answer (mock AI): passages quoted from your documents, not written by a language model.</p>}</>}
                </div>
              ))}
              {asking && <p className="text-sm text-ink-faint" role="status">Searching your documents...</p>}
              <div ref={endRef} />
            </div>
            <form onSubmit={ask} className="flex gap-2 border-t border-paper-line p-3">
              <Input aria-label="Your question" value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. What did I write about my capstone project?" />
              <Button type="submit" variant="accent" disabled={asking || q.trim().length < 2}><Send size={15} /> Ask</Button>
              {msgs.length > 0 && <Button type="button" variant="ghost" onClick={clear}>Clear</Button>}
            </form>
          </Card></TabsContent>
          <TabsContent value="search"><Card><CardContent className="space-y-3 pt-5">
            <form onSubmit={search} className="flex flex-wrap gap-2">
              <Input aria-label="Search query" className="min-w-[200px] flex-1" value={sq} onChange={(e) => setSq(e.target.value)} placeholder="Search your documents" />
              <Select aria-label="Search mode" className="w-36" value={mode} onChange={(e) => setMode(e.target.value)}><option value="hybrid">Hybrid</option><option value="semantic">Semantic</option><option value="lexical">Keyword</option></Select>
              <Button type="submit" variant="accent"><Search size={15} /> Search</Button>
            </form>
            {results && (results.results.length === 0 ? <p className="text-sm text-ink-faint">No matching passages.</p> : (<>
              <p className="text-xs text-ink-faint">mode {results.mode} · reranker {results.reranker} · embeddings {results.embedding}{results.semantic ? "" : " (lexical)"} · store {results.vector_store}</p>
              <ul className="space-y-2">{results.results.map((r: any, i: number) => <li key={`${r.document_id}-${r.chunk_index}`} className="rounded-card border border-paper-line p-3 text-sm"><div className="mb-1 flex justify-between"><span className="font-medium">{i + 1}. {r.filename}</span><span className="font-mono text-xs text-ink-faint">{Number(r.rerank_score ?? r.score).toFixed(3)}</span></div><p className="text-ink-soft">{r.content}</p></li>)}</ul></>))}
          </CardContent></Card></TabsContent>
        </Tabs>

        <Card className="h-fit"><CardHeader><CardTitle>Documents</CardTitle></CardHeader><CardContent className="space-y-3">
          <div><Label htmlFor="dt">Type</Label><Select id="dt" value={docType} onChange={(e) => setDocType(e.target.value)}><option value="notes">Study notes</option><option value="job_description">Job description</option><option value="resume">Resume</option><option value="other">Other</option></Select></div>
          <Button variant="outline" className="w-full" onClick={() => fileRef.current?.click()} disabled={uploading}><UploadCloud size={15} /> {uploading ? "Indexing..." : "Upload PDF, DOCX, TXT or MD"}</Button>
          <input ref={fileRef} type="file" accept=".pdf,.docx,.txt,.md" className="hidden" aria-label="Upload document" onChange={upload} />
          <Button variant="ghost" size="sm" className="w-full" onClick={fromResume}>Index my active resume</Button>
          <ul className="divide-y divide-paper-line">
            {docs.length === 0 && <li className="py-3 text-sm text-ink-faint">No documents yet.</li>}
            {docs.map((d) => <li key={d.id} className="flex items-center gap-2 py-2 text-sm"><FileText size={15} className="shrink-0 text-ink-faint" /><span className="min-w-0 flex-1 truncate" title={d.filename}>{d.filename}<span className="block text-xs text-ink-faint">{d.chunk_count} chunks · {d.doc_type}</span></span><Button variant="ghost" size="icon" aria-label={`Delete ${d.filename}`} onClick={() => remove(d)}><Trash2 size={14} /></Button></li>)}
          </ul>
          {status && <p className="text-xs text-ink-faint">Embeddings: {status.embedding.provider} · {status.vector_store}</p>}
        </CardContent></Card>
      </div>
    </div>
  );
}
