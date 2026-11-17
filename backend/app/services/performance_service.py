import json
from collections import defaultdict
from typing import List

from sqlalchemy.orm import Session

from app.models.performance import PerformanceSnapshot
from app.models.interview import Interview


def _avg(values: List[float]) -> float:
    return round(sum(values) / len(values), 1) if values else 0.0


def get_performance_summary(db: Session, user_id: int) -> dict:
    snapshots = (
        db.query(PerformanceSnapshot)
        .filter(PerformanceSnapshot.user_id == user_id)
        .order_by(PerformanceSnapshot.recorded_at.asc())
        .all()
    )

    by_type = defaultdict(list)
    for s in snapshots:
        by_type[s.source_type].append(s.score)

    hr_scores = by_type.get("hr", [])
    technical_scores = by_type.get("technical", [])
    coding_scores = by_type.get("coding", [])

    interviews = db.query(Interview).filter(Interview.user_id == user_id, Interview.status == "completed").all()
    communication_scores = [i.communication_score for i in interviews if i.communication_score is not None]

    all_scores = hr_scores + technical_scores + coding_scores
    overall_readiness = _avg(all_scores)

    # weak / strong topics from skill_tags weighted by score
    skill_scores = defaultdict(list)
    for s in snapshots:
        try:
            tags = json.loads(s.skill_tags or "[]")
        except json.JSONDecodeError:
            tags = []
        for tag in tags:
            skill_scores[tag].append(s.score)

    topic_avgs = sorted(((tag, _avg(scores)) for tag, scores in skill_scores.items()), key=lambda x: x[1])
    weak_topics = [t for t, avg in topic_avgs if avg < 70][:5]
    strong_topics = [t for t, avg in reversed(topic_avgs) if avg >= 75][:5]
    topic_scores = [{"topic": t, "score": avg, "attempts": len(skill_scores[t])} for t, avg in topic_avgs]
    # recommended = weakest first; if nothing is weak yet, the lowest-scoring topics still deserve practice
    recommended_topics = (weak_topics or [t for t, _ in topic_avgs])[:4]
    mastered = [t for t, avg in topic_avgs if avg >= 75]
    preparation_progress = round(100 * len(mastered) / len(topic_avgs), 1) if topic_avgs else 0.0

    trend = [
        {"date": s.recorded_at.strftime("%Y-%m-%d"), "score": s.score, "source_type": s.source_type}
        for s in snapshots
    ]

    return {
        "overall_readiness": overall_readiness,
        "technical_score": _avg(technical_scores),
        "hr_score": _avg(hr_scores),
        "coding_score": _avg(coding_scores),
        "communication_score": _avg(communication_scores),
        "total_interviews": len(interviews),
        "total_coding_attempts": len(coding_scores),
        "weak_topics": weak_topics,
        "strong_topics": strong_topics,
        "score_trend": trend,
        "topic_scores": topic_scores,
        "recommended_topics": recommended_topics,
        "preparation_progress": preparation_progress,
    }
