import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, LineChart, Line, Cell, ReferenceLine,
} from "recharts";
import { getPerformance, getErrorMessage } from "../services/api";
import { Card, Badge, SectionHeading } from "../components/ui/Primitives";
import { Loader, ErrorState, EmptyState } from "../components/ui/States";

const TOOLTIP_STYLE = { borderRadius: 6, border: "1px solid #E4E5DF", fontSize: 12 };
const AXIS = { fontSize: 11, fill: "rgb(var(--ink-faint))" };
const topicColor = (score) => (score >= 75 ? "rgb(var(--teal))" : score < 70 ? "rgb(var(--clay))" : "rgb(var(--amber))");

function TrendCard({ title, points, color }) {
  const data = points.map((p, i) => ({ attempt: i + 1, score: p.score, date: p.date }));
  return (
    <Card className="p-5">
      <h3 className="font-display text-base mb-3">{title}</h3>
      {data.length === 0 ? (
        <p className="text-sm text-ink-faint py-8 text-center">No attempts yet.</p>
      ) : (
        <ResponsiveContainer width="100%" height={150}>
          <LineChart data={data}>
            <CartesianGrid stroke="rgb(var(--line))" vertical={false} />
            <XAxis dataKey="attempt" tick={AXIS} label={{ value: "Attempt", position: "insideBottom", offset: -2, fontSize: 10, fill: "rgb(var(--ink-faint))" }} />
            <YAxis domain={[0, 100]} tick={AXIS} width={28} />
            <Tooltip contentStyle={TOOLTIP_STYLE} labelFormatter={(v) => `Attempt ${v}`} />
            <Line type="monotone" dataKey="score" stroke={color} strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}

export default function Performance() {
  const [perf, setPerf] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await getPerformance();
      setPerf(res.data);
    } catch (err) {
      setError(getErrorMessage(err, "Could not load performance data."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <Loader label="Loading performance data..." />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  const hasData = perf.total_interviews > 0 || perf.total_coding_attempts > 0;
  if (!hasData) {
    return (
      <div>
        <SectionHeading title="Performance Analytics" description="A breakdown of every interview and coding attempt." />
        <EmptyState title="No attempts recorded yet" description="Complete an interview or a coding problem and your charts will appear here." />
      </div>
    );
  }

  const byType = (type) => perf.score_trend.filter((p) => p.source_type === type);
  const categoryData = [
    { name: "HR", score: perf.hr_score },
    { name: "Technical", score: perf.technical_score },
    { name: "Coding", score: perf.coding_score },
    { name: "Communication", score: perf.communication_score },
  ];
  const topicData = perf.topic_scores.map((t) => ({ ...t, label: t.topic.replace(/_/g, " ") }));

  return (
    <div>
      <SectionHeading title="Performance Analytics" description="A breakdown of every interview and coding attempt you've made so far." />

      <div className="grid md:grid-cols-2 gap-6 mb-6">
        <Card className="p-6">
          <h3 className="font-display text-lg mb-4">Score by category</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={categoryData}>
              <CartesianGrid stroke="rgb(var(--line))" vertical={false} />
              <XAxis dataKey="name" tick={{ ...AXIS, fontSize: 12 }} />
              <YAxis domain={[0, 100]} tick={{ ...AXIS, fontSize: 12 }} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Bar dataKey="score" fill="rgb(var(--amber))" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-6">
          <h3 className="font-display text-lg mb-4">Score over time (all attempts)</h3>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={perf.score_trend.map((p, i) => ({ ...p, attempt: i + 1 }))}>
              <CartesianGrid stroke="rgb(var(--line))" vertical={false} />
              <XAxis dataKey="date" tick={AXIS} />
              <YAxis domain={[0, 100]} tick={AXIS} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Line type="monotone" dataKey="score" stroke="rgb(var(--teal))" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <div className="grid md:grid-cols-3 gap-6 mb-6">
        <TrendCard title="HR performance" points={byType("hr")} color="rgb(var(--teal))" />
        <TrendCard title="Technical performance" points={byType("technical")} color="rgb(var(--amber))" />
        <TrendCard title="Coding performance" points={byType("coding")} color="rgb(var(--clay))" />
      </div>

      <Card className="p-6 mb-6">
        <div className="flex items-center justify-between mb-1">
          <h3 className="font-display text-lg">Strong and weak topics</h3>
          <div className="flex gap-2">
            <Badge tone="teal">75+ strong</Badge><Badge tone="amber">70-74</Badge><Badge tone="clay">under 70 weak</Badge>
          </div>
        </div>
        <p className="text-sm text-ink-faint mb-4">Average score per topic across all attempts.</p>
        <ResponsiveContainer width="100%" height={Math.max(160, topicData.length * 38)}>
          <BarChart data={topicData} layout="vertical" margin={{ left: 20 }}>
            <CartesianGrid stroke="rgb(var(--line))" horizontal={false} />
            <XAxis type="number" domain={[0, 100]} tick={AXIS} />
            <YAxis type="category" dataKey="label" tick={{ ...AXIS, fontSize: 12 }} width={110} />
            <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v, _n, item) => [`${v} (${item.payload.attempts} attempt${item.payload.attempts > 1 ? "s" : ""})`, "Average"]} />
            <ReferenceLine x={70} stroke="rgb(var(--clay))" strokeDasharray="4 4" />
            <ReferenceLine x={75} stroke="rgb(var(--teal))" strokeDasharray="4 4" />
            <Bar dataKey="score" radius={[0, 4, 4, 0]}>
              {topicData.map((t) => <Cell key={t.topic} fill={topicColor(t.score)} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <div className="grid md:grid-cols-2 gap-6 mb-6">
        <Card className="p-6">
          <h3 className="font-display text-lg mb-3">Weak topics</h3>
          <div className="flex flex-wrap gap-2">
            {perf.weak_topics.length
              ? perf.weak_topics.map((t) => <Badge key={t} tone="clay">{t.replace(/_/g, " ")}</Badge>)
              : <p className="text-sm text-ink-faint">None below 70 right now.</p>}
          </div>
        </Card>
        <Card className="p-6">
          <h3 className="font-display text-lg mb-3">Strong topics</h3>
          <div className="flex flex-wrap gap-2">
            {perf.strong_topics.length
              ? perf.strong_topics.map((t) => <Badge key={t} tone="teal">{t.replace(/_/g, " ")}</Badge>)
              : <p className="text-sm text-ink-faint">None at 75+ yet.</p>}
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Card className="p-5 text-center">
          <p className="text-xs text-ink-faint mb-1">Total interviews</p>
          <p className="font-mono text-2xl">{perf.total_interviews}</p>
        </Card>
        <Card className="p-5 text-center">
          <p className="text-xs text-ink-faint mb-1">Coding attempts</p>
          <p className="font-mono text-2xl">{perf.total_coding_attempts}</p>
        </Card>
      </div>
    </div>
  );
}
