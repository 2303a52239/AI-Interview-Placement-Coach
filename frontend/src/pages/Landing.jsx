import { Link } from "react-router-dom";
import { Mic, Code2, LineChart, FileSearch, ArrowRight, CheckCircle2, Users } from "lucide-react";

const STEPS = [
  { n: "Upload", text: "Add your resume. We extract skills, projects, and experience automatically." },
  { n: "Practice", text: "Take HR, technical, or coding rounds tailored to your target role." },
  { n: "Improve", text: "Get scored feedback, track weak spots, and follow a plan that adapts." },
];

const STACK = ["React", "FastAPI", "PostgreSQL", "Java", "RAG Pipeline", "Speech-to-Text"];

export default function Landing() {
  return (
    <div className="bg-paper text-ink">
      {/* ---------- Top bar ---------- */}
      <header className="max-w-6xl mx-auto px-6 py-6 flex items-center justify-between">
        <p className="font-display text-lg">Placement Coach</p>
        <div className="flex items-center gap-3">
          <Link to="/login" className="text-sm px-4 py-2 text-ink hover:text-amber-dark transition-colors">
            Log in
          </Link>
          <Link
            to="/register"
            className="text-sm px-4 py-2 bg-ink text-paper rounded-card hover:bg-ink-soft transition-colors"
          >
            Get started
          </Link>
        </div>
      </header>

      {/* ---------- Hero ---------- */}
      <section className="max-w-6xl mx-auto px-6 pt-10 pb-20 grid md:grid-cols-2 gap-12 items-center">
        <div>
          <p className="text-sm text-teal font-medium mb-4">AI-powered placement preparation</p>
          <h1 className="font-display text-4xl md:text-5xl leading-[1.1] mb-6">
            Walk into every interview like you've already done it once.
          </h1>
          <p className="text-ink-faint text-base leading-relaxed mb-8 max-w-md">
            Placement Coach runs personalized HR rounds, technical rounds, and Java coding
            assessments built from your own resume and target role — then tells you exactly
            what to fix before the real thing.
          </p>
          <div className="flex items-center gap-4">
            <Link
              to="/register"
              className="inline-flex items-center gap-2 px-5 py-3 bg-amber text-ink font-medium rounded-card hover:bg-amber-dark transition-colors"
            >
              Get started <ArrowRight size={16} />
            </Link>
            <Link to="/login" className="text-sm underline text-ink-faint hover:text-ink">
              I already have an account
            </Link>
          </div>
        </div>

        {/* Mock interview panel — grounded in the actual product, not a generic illustration */}
        <div className="bg-ink text-paper rounded-card p-6 tick-corner relative">
          <div className="flex items-center justify-between mb-4 text-xs text-white/50 font-mono">
            <span>TECHNICAL ROUND · Question 2 of 5</span>
            <span>04:12</span>
          </div>
          <p className="font-display text-lg mb-5 leading-snug">
            "Explain how HashMap works internally in Java."
          </p>
          <div className="border border-white/15 rounded-card p-4 mb-4 min-h-[70px] text-sm text-white/70 font-mono">
            HashMap stores key-value pairs using an array of buckets. Each key's hashCode()
            determines the bucket index...
          </div>
          <div className="flex items-center justify-between">
            <button className="flex items-center gap-2 text-sm text-white/70">
              <Mic size={16} /> Record answer
            </button>
            <button className="text-sm px-4 py-2 bg-amber text-ink rounded-card font-medium">
              Submit
            </button>
          </div>
          <div className="mt-5 pt-4 border-t border-white/10 flex items-center justify-between text-xs text-white/50">
            <span>Difficulty: Medium</span>
            <span className="font-mono text-amber">Last score: 82</span>
          </div>
        </div>
      </section>

      {/* ---------- How it works ---------- */}
      <section className="bg-paper-panel border-y border-paper-line py-16">
        <div className="max-w-6xl mx-auto px-6">
          <p className="text-sm text-teal font-medium mb-2">How it works</p>
          <h2 className="font-display text-2xl mb-10">Three rounds, one continuously updating plan.</h2>
          <div className="grid md:grid-cols-3 gap-8">
            {STEPS.map((s, i) => (
              <div key={s.n} className="border-t-2 border-amber pt-4">
                <p className="font-mono text-xs text-ink-faint mb-2">STEP {i + 1}</p>
                <h3 className="font-display text-lg mb-2">{s.n}</h3>
                <p className="text-sm text-ink-faint leading-relaxed">{s.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ---------- Features ---------- */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <p className="text-sm text-teal font-medium mb-2">What's inside</p>
        <h2 className="font-display text-2xl mb-10">Everything a real placement cycle throws at you.</h2>
        <div className="grid md:grid-cols-2 gap-6">
          {[
            { icon: FileSearch, title: "Resume-aware questions", text: "Upload a PDF or DOCX resume; questions and difficulty adapt to what's actually on it." },
            { icon: Users, title: "HR + Technical rounds", text: "Structured HR questions and technical questions matched to your listed skills — Java, Python, React, SQL, and more." },
            { icon: Code2, title: "Java coding assessments", text: "Real compilation and execution against test cases, with time and space complexity feedback." },
            { icon: LineChart, title: "Analytics that adapt", text: "Every attempt updates your readiness score and regenerates a prioritized preparation plan." },
          ].map((f) => (
            <div key={f.title} className="p-6 border border-paper-line rounded-card bg-paper-panel">
              <f.icon className="text-amber-dark mb-3" size={22} />
              <h3 className="font-medium mb-1">{f.title}</h3>
              <p className="text-sm text-ink-faint leading-relaxed">{f.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ---------- Tech stack ---------- */}
      <section className="border-t border-paper-line py-12">
        <div className="max-w-6xl mx-auto px-6">
          <p className="text-xs font-mono text-ink-faint mb-4">BUILT WITH</p>
          <div className="flex flex-wrap gap-x-8 gap-y-3">
            {STACK.map((s) => (
              <span key={s} className="flex items-center gap-2 text-sm text-ink-soft">
                <CheckCircle2 size={14} className="text-teal" /> {s}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ---------- CTA ---------- */}
      <section className="bg-ink text-paper py-16">
        <div className="max-w-6xl mx-auto px-6 text-center">
          <h2 className="font-display text-3xl mb-4">Your first mock interview takes two minutes to start.</h2>
          <Link
            to="/register"
            className="inline-flex items-center gap-2 px-6 py-3 bg-amber text-ink font-medium rounded-card hover:bg-amber-dark transition-colors mt-4"
          >
            Create your free account <ArrowRight size={16} />
          </Link>
        </div>
      </section>

      <footer className="py-8 text-center text-xs text-ink-faint">
        Placement Coach — a demo project. AI evaluation runs on a local mock provider by default.
      </footer>
    </div>
  );
}
