import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { getPreparationPlan, regeneratePreparationPlan, getErrorMessage } from "../services/api";
import { useToast } from "../context/ToastContext";
import { useConfirm } from "../context/ConfirmContext";
import { Card, Button, Badge, SectionHeading } from "../components/ui/Primitives";
import { Loader, ErrorState } from "../components/ui/States";

const PRIORITY_TONE = { high: "clay", medium: "amber", low: "teal" };

export default function PreparationPlan() {
  const { showToast } = useToast();
  const confirm = useConfirm();
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await getPreparationPlan();
      setPlan(res.data);
    } catch (err) {
      setError(getErrorMessage(err, "Could not load your preparation plan."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleRegenerate = async () => {
    const ok = await confirm({
      title: "Regenerate your plan?",
      message: "Your current plan will be replaced by a new one based on your latest results.",
      confirmLabel: "Regenerate",
    });
    if (!ok) return;
    setRegenerating(true);
    try {
      const res = await regeneratePreparationPlan();
      setPlan(res.data);
      showToast("Preparation plan updated based on your latest results.", "success");
    } catch (err) {
      showToast(getErrorMessage(err, "Could not regenerate your plan."), "error");
    } finally {
      setRegenerating(false);
    }
  };

  if (loading) return <Loader label="Loading your preparation plan..." />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <SectionHeading
          title="Preparation Plan"
          description="Prioritized based on your weakest scoring topics. Updates automatically after each attempt."
        />
        <Button variant="outline" onClick={handleRegenerate} disabled={regenerating}>
          <RefreshCw size={15} className={regenerating ? "animate-spin" : ""} /> Regenerate
        </Button>
      </div>

      <p className="text-xs text-ink-faint mb-4">
        Last generated: {new Date(plan.generated_at).toLocaleString()}
      </p>

      {plan.weekly_schedule?.length > 0 && (
        <Card className="p-6 mb-6">
          <h3 className="font-display text-lg mb-1">This week</h3>
          <p className="text-sm text-ink-faint mb-4">High-priority topics get the most days.</p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {plan.weekly_schedule.map((d) => (
              <div key={d.day} className="border border-paper-line rounded-card p-3">
                <p className="font-mono text-xs text-ink-faint uppercase mb-1">{d.day}</p>
                <p className="text-sm font-medium mb-1">{d.focus}</p>
                <p className="text-xs text-ink-faint leading-relaxed">{d.activity}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      <h3 className="font-display text-lg mb-3">Priority topics</h3>
      <div className="space-y-4">
        {plan.items.map((item, i) => (
          <Card key={i} className="p-5 flex items-start justify-between gap-6">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <h3 className="font-display text-lg">{item.topic}</h3>
                <Badge tone={PRIORITY_TONE[item.priority] || "neutral"}>{item.priority} priority</Badge>
              </div>
              <p className="text-sm text-ink-soft mb-2">{item.recommendation}</p>
              <p className="text-sm text-ink-faint"><span className="font-medium text-ink">Practice: </span>{item.suggested_practice}</p>
            </div>
            <Badge tone="neutral">{item.schedule}</Badge>
          </Card>
        ))}
      </div>
    </div>
  );
}
