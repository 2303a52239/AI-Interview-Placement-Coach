"""Analytics computed from stored records only. Nothing here is estimated or randomised: if there is no data, the
fields are empty/zero and the UI shows an empty state."""
import datetime as dt
import json
from collections import Counter, defaultdict
from typing import Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.coding import CodingQuestion, CodingSubmission
from app.models.interview import Interview, InterviewQuestion, InterviewAnswer, Evaluation
from app.models.performance import PerformanceSnapshot
from app.models.roadmap import Roadmap, RoadmapTask
from app.services import adaptive_engine as eng
from app.services import skill_gap_service as sg


def _week_key(d: dt.datetime) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def _streak(days: set) -> Dict[str, int]:
    today = dt.date.today()
    cur = 0
    d = today if today in days else today - dt.timedelta(days=1)
    while d in days:
        cur += 1
        d -= dt.timedelta(days=1)
    longest, run, prev = 0, 0, None
    for day in sorted(days):
        run = run + 1 if prev and (day - prev).days == 1 else 1
        longest = max(longest, run)
        prev = day
    return {"current": cur, "longest": longest}


def student_analytics(db: Session, user_id: int) -> Dict:
    snaps = (db.query(PerformanceSnapshot).filter(PerformanceSnapshot.user_id == user_id)
             .order_by(PerformanceSnapshot.recorded_at).all())

    def when(x):
        return x.recorded_at or dt.datetime.utcnow()

    weekly: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    for s in snaps:
        weekly[_week_key(when(s))][s.source_type].append(s.score)
    weeks = sorted(weekly)[-12:]
    trend = [{"week": w, "overall": round(sum(sum(v) for v in weekly[w].values()) / max(1, sum(len(v) for v in weekly[w].values())), 1),
              **{k: round(sum(v) / len(v), 1) for k, v in weekly[w].items()}} for w in weeks]

    # topic mastery merges interview + coding evidence
    interview = eng.topic_history(db, user_id)
    coding = sg.coding_topic_scores(db, user_id)
    topics = []
    for t in sorted(set(interview) | set(coding)):
        i, c = interview.get(t), coding.get(t)
        parts = [x["avg"] for x in (i, c) if x]
        topics.append({"topic": t, "score": round(sum(parts) / len(parts), 1),
                       "interview_score": round(i["avg"], 1) if i else None, "coding_score": round(c["avg"], 1) if c else None,
                       "attempts": (i["attempts"] if i else 0) + (c["attempts"] if c else 0)})
    topics.sort(key=lambda x: x["score"])

    # rubric criteria averages
    crit: Dict[str, List[float]] = defaultdict(list)
    rows = (db.query(Evaluation.rubric).join(InterviewAnswer, InterviewAnswer.id == Evaluation.answer_id)
            .join(InterviewQuestion, InterviewQuestion.id == InterviewAnswer.question_id)
            .join(Interview, Interview.id == InterviewQuestion.interview_id).filter(Interview.user_id == user_id).all())
    for (r,) in rows:
        for k, v in json.loads(r or "{}").items():
            crit[k].append(float(v.get("score", 0)))
    rubric = {k: round(sum(v) / len(v), 1) for k, v in crit.items()}

    # speech
    sp = (db.query(InterviewAnswer.speech_metrics).join(InterviewQuestion, InterviewQuestion.id == InterviewAnswer.question_id)
          .join(Interview, Interview.id == InterviewQuestion.interview_id)
          .filter(Interview.user_id == user_id, InterviewAnswer.input_mode == "voice").all())
    metrics = [json.loads(m) for (m,) in sp if m]
    wpms = [m["wpm"] for m in metrics if m.get("wpm")]
    speech = {"voice_answers": len(metrics), "avg_wpm": round(sum(wpms) / len(wpms), 1) if wpms else None,
              "avg_filler_ratio": round(sum(m.get("filler_ratio", 0) for m in metrics) / len(metrics), 3) if metrics else None}

    # coding breakdown
    subs = (db.query(CodingSubmission, CodingQuestion.difficulty).join(CodingQuestion, CodingQuestion.id == CodingSubmission.question_id)
            .filter(CodingSubmission.user_id == user_id, CodingSubmission.status != "sandbox_error").all())
    by_lang: Dict[str, List[float]] = defaultdict(list)
    by_diff: Dict[str, List[float]] = defaultdict(list)
    for s, diff in subs:
        by_lang[s.language].append(s.score or 0)
        by_diff[diff].append(s.score or 0)
    solved = {s.question_id for s, _ in subs if (s.score or 0) >= 100}
    coding_stats = {"submissions": len(subs), "problems_solved": len(solved),
                    "status": dict(Counter(s.status for s, _ in subs)),
                    "by_language": {k: {"avg": round(sum(v) / len(v), 1), "count": len(v)} for k, v in by_lang.items()},
                    "by_difficulty": {k: {"avg": round(sum(v) / len(v), 1), "count": len(v)} for k, v in by_diff.items()}}

    # activity per day (last 90 days) and streak
    since = dt.datetime.utcnow() - dt.timedelta(days=90)
    activity: Counter = Counter()
    for (d,) in db.query(Interview.started_at).filter(Interview.user_id == user_id, Interview.started_at >= since):
        activity[d.date().isoformat()] += 1
    for (d,) in db.query(CodingSubmission.submitted_at).filter(CodingSubmission.user_id == user_id, CodingSubmission.submitted_at >= since):
        activity[d.date().isoformat()] += 1
    for (d,) in db.query(RoadmapTask.completed_at).join(Roadmap, Roadmap.id == RoadmapTask.roadmap_id).filter(
            Roadmap.user_id == user_id, RoadmapTask.completed_at.isnot(None), RoadmapTask.completed_at >= since):
        activity[d.date().isoformat()] += 1
    days = {dt.date.fromisoformat(k) for k in activity}

    ivs = db.query(func.count(Interview.id), func.avg(Interview.overall_score)).filter(
        Interview.user_id == user_id, Interview.status == "completed", Interview.overall_score.isnot(None)).one()
    by_type = dict(db.query(Interview.interview_type, func.avg(Interview.overall_score)).filter(
        Interview.user_id == user_id, Interview.status == "completed", Interview.overall_score.isnot(None)).group_by(Interview.interview_type).all())
    return {
        "overview": {"interviews_completed": int(ivs[0] or 0), "avg_interview_score": round(float(ivs[1]), 1) if ivs[1] is not None else None,
                     "coding_submissions": coding_stats["submissions"], "problems_solved": coding_stats["problems_solved"],
                     "active_days_90": len(days), "streak": _streak(days)},
        "interview_by_type": {k: round(float(v), 1) for k, v in by_type.items()},
        "trend": trend, "topics": topics, "rubric": rubric, "speech": speech, "coding": coding_stats,
        "activity": [{"date": k, "count": v} for k, v in sorted(activity.items())],
        "has_data": bool(snaps or subs or rows),
    }
