"""Institution-level aggregates for admins and placement officers (real rows only)."""
import csv
import datetime as dt
import io
import json
from collections import Counter, defaultdict
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai.factory import ai_status
from app.models.coding import CodingSubmission, CodingAssessment, CodingQuestion
from app.models.interview import Interview, InterviewQuestion, InterviewAnswer, Evaluation
from app.models.rag import TokenUsage
from app.models.user import User, Profile
from app.services import profile_service as ps


def student_query(db: Session, search: Optional[str] = None, branch: Optional[str] = None, year: Optional[int] = None):
    q = db.query(User, Profile).outerjoin(Profile, Profile.user_id == User.id).filter(User.role == "student")
    if search:
        like = f"%{search.lower()}%"
        q = q.filter(func.lower(User.name).like(like) | func.lower(User.email).like(like))
    if branch:
        q = q.filter(func.lower(Profile.branch) == branch.lower())
    if year:
        q = q.filter(Profile.graduation_year == year)
    return q.order_by(User.id)


def student_row(db: Session, u: User, p: Optional[Profile]) -> Dict:
    iv = db.query(func.count(Interview.id), func.avg(Interview.overall_score)).filter(
        Interview.user_id == u.id, Interview.status == "completed", Interview.overall_score.isnot(None)).one()
    cd = db.query(func.count(CodingSubmission.id), func.avg(CodingSubmission.score)).filter(
        CodingSubmission.user_id == u.id, CodingSubmission.status != "sandbox_error").one()
    r = ps.readiness(db, u)
    return {"user_id": u.id, "name": u.name, "email": u.email, "is_active": u.is_active, "role": u.role,
            "branch": (p.branch if p else "") or "", "graduation_year": p.graduation_year if p else None,
            "cgpa": p.cgpa if p else None, "college": (p.college if p else "") or "",
            "total_interviews": int(iv[0] or 0), "average_score": round(float(iv[1]), 1) if iv[1] is not None else 0.0,
            "coding_submissions": int(cd[0] or 0), "coding_avg": round(float(cd[1]), 1) if cd[1] is not None else None,
            "readiness": r["score"], "readiness_band": r["band"], "last_login_at": u.last_login_at, "created_at": u.created_at}


def institution_analytics(db: Session) -> Dict:
    students = db.query(User).filter(User.role == "student")
    total_students = students.count()
    active_30 = db.query(func.count(func.distinct(Interview.user_id))).filter(
        Interview.started_at >= dt.datetime.utcnow() - dt.timedelta(days=30)).scalar() or 0

    weekly: Counter = Counter()
    for (d,) in db.query(User.created_at).filter(User.role == "student"):
        if d:
            y, w, _ = d.isocalendar()
            weekly[f"{y}-W{w:02d}"] += 1

    by_type = {k: {"avg": round(float(a), 1), "count": int(c)} for k, a, c in db.query(
        Interview.interview_type, func.avg(Interview.overall_score), func.count(Interview.id)).filter(
        Interview.status == "completed", Interview.overall_score.isnot(None)).group_by(Interview.interview_type)}

    topic_rows = (db.query(InterviewQuestion.skill_tag, func.avg(Evaluation.score), func.count(Evaluation.id))
                  .join(InterviewAnswer, InterviewAnswer.question_id == InterviewQuestion.id)
                  .join(Evaluation, Evaluation.answer_id == InterviewAnswer.id).group_by(InterviewQuestion.skill_tag).all())
    topics = sorted([{"topic": t, "avg": round(float(a), 1), "answers": int(c)} for t, a, c in topic_rows], key=lambda x: x["avg"])

    subs = db.query(CodingSubmission.status, func.count(CodingSubmission.id)).group_by(CodingSubmission.status).all()
    by_lang = {l: int(c) for l, c in db.query(CodingSubmission.language, func.count(CodingSubmission.id)).group_by(CodingSubmission.language)}
    hardest = [{"question": t, "avg_score": round(float(a), 1), "submissions": int(c)} for t, a, c in
               db.query(CodingQuestion.title, func.avg(CodingSubmission.score), func.count(CodingSubmission.id))
               .join(CodingSubmission, CodingSubmission.question_id == CodingQuestion.id).group_by(CodingQuestion.id, CodingQuestion.title)
               .order_by(func.avg(CodingSubmission.score)).limit(5)]

    dist = Counter()
    for u, p in student_query(db).limit(500):
        band = ps.readiness(db, u)["band"]
        dist[band] += 1

    tok = db.query(TokenUsage.feature, TokenUsage.provider, func.sum(TokenUsage.prompt_tokens), func.sum(TokenUsage.completion_tokens),
                   func.count(TokenUsage.id)).group_by(TokenUsage.feature, TokenUsage.provider).all()
    tokens = [{"feature": f, "provider": p, "prompt_tokens": int(a or 0), "completion_tokens": int(b or 0), "calls": int(c)} for f, p, a, b, c in tok]
    return {
        "totals": {"students": total_students, "active_last_30_days": int(active_30),
                   "interviews_completed": int(sum(v["count"] for v in by_type.values())),
                   "coding_submissions": int(sum(c for _, c in subs)),
                   "timed_assessments": db.query(CodingAssessment).count()},
        "signups_by_week": [{"week": k, "count": v} for k, v in sorted(weekly.items())][-12:],
        "interview_by_type": by_type, "topic_averages": topics,
        "coding": {"status": {s: int(c) for s, c in subs}, "by_language": by_lang, "hardest_questions": hardest},
        "readiness_distribution": dict(dist),
        "ai": {**ai_status(), "token_usage": tokens,
               "total_tokens": sum(t["prompt_tokens"] + t["completion_tokens"] for t in tokens)},
    }


def institution_csv(db: Session, branch=None, year=None) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["name", "email", "college", "branch", "graduation_year", "cgpa", "interviews_completed", "avg_interview_score",
                "coding_submissions", "avg_coding_score", "readiness_score", "readiness_band"])
    for u, p in student_query(db, None, branch, year):
        r = student_row(db, u, p)
        w.writerow([r["name"], r["email"], r["college"], r["branch"], r["graduation_year"] or "", r["cgpa"] or "",
                    r["total_interviews"], r["average_score"], r["coding_submissions"], r["coding_avg"] if r["coding_avg"] is not None else "",
                    r["readiness"], r["readiness_band"]])
    return out.getvalue()
