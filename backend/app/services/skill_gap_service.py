"""Skill-gap analysis from real data: claimed skills, resume, interview topic scores, coding topic scores."""
import json
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.data.roles import ROLES, SKILL_TOPICS, PROFICIENCY_SCORE
from app.data.skills import canonical
from app.models.coding import CodingQuestion, CodingSubmission
from app.models.resume import Resume, Skill
from app.models.user import Profile
from app.services import adaptive_engine as eng
from app.services import resume_service as rs

TARGET_LEVEL = 75.0


def available_roles() -> List[str]:
    return list(ROLES)


def resolve_role(name: Optional[str]) -> str:
    if not name:
        return "Software Developer"
    low = name.lower()
    for r in ROLES:
        if r.lower() == low:
            return r
    for r in ROLES:
        if low in r.lower() or r.lower() in low:
            return r
    return "Software Developer"


def coding_topic_scores(db: Session, user_id: int) -> Dict[str, Dict[str, float]]:
    rows = (db.query(CodingQuestion.topic_tag, CodingSubmission.score).join(
        CodingQuestion, CodingQuestion.id == CodingSubmission.question_id).filter(CodingSubmission.user_id == user_id,
                                                                                    CodingSubmission.status != "sandbox_error").all())
    agg: Dict[str, List[float]] = {}
    for tag, score in rows:
        agg.setdefault(tag, []).append(score or 0)
    return {t: {"avg": sum(v) / len(v), "attempts": len(v)} for t, v in agg.items()}


def analyze(db: Session, user_id: int, role: Optional[str] = None) -> Dict:
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    role = resolve_role(role or (profile.target_role if profile else None))
    required = ROLES[role]

    claimed: Dict[str, str] = {canonical(s.name): (s.proficiency or "intermediate") for s in db.query(Skill).filter(Skill.user_id == user_id)}
    resume = db.query(Resume).filter(Resume.user_id == user_id, Resume.is_active == True).first()  # noqa: E712
    on_resume = {canonical(s) for s in rs.all_skills_of(resume)} if resume else set()
    interview = eng.topic_history(db, user_id)
    coding = coding_topic_scores(db, user_id)

    items = []
    for skill, importance in required.items():
        evidence = []
        measured: List[float] = []
        for topic in SKILL_TOPICS.get(skill, []):
            if topic in interview:
                measured.append(interview[topic]["avg"])
                evidence.append(f"Interview '{topic}': {interview[topic]['avg']:.0f}/100 over {interview[topic]['attempts']} answer(s)")
            if topic in coding:
                measured.append(coding[topic]["avg"])
                evidence.append(f"Coding '{topic}': {coding[topic]['avg']:.0f}/100 over {coding[topic]['attempts']} submission(s)")
        claim = PROFICIENCY_SCORE.get(claimed.get(skill, ""), None)
        if skill in claimed:
            evidence.append(f"Listed on profile as {claimed[skill]}")
        if skill in on_resume:
            evidence.append("Mentioned on resume")
        if measured:
            current = sum(measured) / len(measured)
            state = "verified_strong" if current >= TARGET_LEVEL else "weak"
        elif claim is not None or skill in on_resume:
            current = (claim if claim is not None else 45) * 0.8   # claimed but unverified: discounted
            state = "unverified"
        else:
            current = 0.0
            state = "missing"
        gap = max(0.0, TARGET_LEVEL - current)
        items.append({"skill": skill, "importance": importance, "current": round(current, 1), "target": TARGET_LEVEL,
                      "gap": round(gap, 1), "priority_score": round(gap * importance, 1), "state": state,
                      "topics": SKILL_TOPICS.get(skill, []), "evidence": evidence or ["No evidence yet"]})
    items.sort(key=lambda x: (-x["priority_score"], x["skill"]))
    total_w = sum(required.values()) * TARGET_LEVEL
    coverage = 100 * (1 - sum(i["priority_score"] for i in items) / total_w) if total_w else 0
    return {"role": role, "role_fit_score": round(max(0.0, min(100.0, coverage)), 1), "gaps": items,
            "summary": {s: sum(1 for i in items if i["state"] == s) for s in ("missing", "unverified", "weak", "verified_strong")},
            "has_resume": bool(resume), "has_measurements": bool(interview or coding),
            "note": "Unverified skills are discounted until you demonstrate them in an interview or coding attempt."}
