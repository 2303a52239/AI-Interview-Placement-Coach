import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getInterviewHistory, getErrorMessage } from "../services/api";
import { Card, Badge, SectionHeading } from "../components/ui/Primitives";
import { Loader, ErrorState, EmptyState } from "../components/ui/States";

export default function InterviewHistory() {
  const [interviews, setInterviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await getInterviewHistory();
      setInterviews(res.data);
    } catch (err) {
      setError(getErrorMessage(err, "Could not load interview history."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <Loader label="Loading history..." />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <div>
      <SectionHeading title="Interview History" description="Every HR and technical round you've attempted." />

      {interviews.length === 0 ? (
        <EmptyState title="No interviews yet" description="Your completed and in-progress interviews will appear here." />
      ) : (
        <div className="space-y-3">
          {interviews.map((iv) => (
            <Link key={iv.id} to={`/history/${iv.id}`}>
              <Card className="p-5 hover:border-amber transition-colors">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium capitalize">{iv.interview_type} Interview</p>
                    <p className="text-xs text-ink-faint">
                      {new Date(iv.started_at).toLocaleString()}
                      {iv.duration_seconds > 0 && ` · ${Math.max(1, Math.round(iv.duration_seconds / 60))} min`}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge tone={iv.difficulty === "hard" ? "clay" : iv.difficulty === "easy" ? "teal" : "amber"}>{iv.difficulty}</Badge>
                    <Badge tone={iv.status === "completed" ? "teal" : "amber"}>{iv.status}</Badge>
                    {iv.overall_score != null && <span className="font-mono text-lg text-ink">{iv.overall_score}</span>}
                  </div>
                </div>
                {(iv.strengths.length > 0 || iv.weaknesses.length > 0) && (
                  <div className="grid md:grid-cols-2 gap-4 mt-4 pt-4 border-t border-paper-line text-sm">
                    <div>
                      <p className="text-xs font-mono text-teal uppercase mb-1">Strengths</p>
                      <ul className="list-disc pl-4 text-ink-soft space-y-0.5">
                        {iv.strengths.slice(0, 2).map((x, i) => <li key={i}>{x}</li>)}
                      </ul>
                    </div>
                    <div>
                      <p className="text-xs font-mono text-clay uppercase mb-1">Weaknesses</p>
                      <ul className="list-disc pl-4 text-ink-soft space-y-0.5">
                        {iv.weaknesses.slice(0, 2).map((x, i) => <li key={i}>{x}</li>)}
                      </ul>
                    </div>
                  </div>
                )}
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
