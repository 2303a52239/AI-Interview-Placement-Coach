"""Personalised roadmap: daily/weekly tasks, spaced revision, progress, and dynamic re-planning."""
import datetime as dt
import json
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.data.roles import TOPIC_STUDY_NOTES, SKILL_TOPICS
from app.models.roadmap import Roadmap, RoadmapTask
from app.services import skill_gap_service as sg

REVISION_OFFSETS = (2, 5, 12)  # days after the study day (spaced repetition)
TOPIC_TITLES = {"dsa": "Data Structures & Algorithms", "system_design": "System Design", "dbms": "DBMS", "cn": "Computer Networks",
                "os": "Operating Systems", "sql": "SQL", "ml": "Machine Learning", "dl": "Deep Learning", "nlp": "NLP",
                "genai": "Generative AI", "llm": "LLMs", "rag": "RAG", "python": "Python", "java": "Java", "hr": "HR / Behavioural"}


def _priority_topics(gaps: Dict, limit: int = 8) -> List[Dict]:
    """Collapse skill gaps into practice topics, ranked by total priority."""
    scores: Dict[str, float] = {}
    reasons: Dict[str, List[str]] = {}
    for g in gaps["gaps"]:
        if g["state"] == "verified_strong":
            continue
        for t in g["topics"][:2] if g["topics"] else []:
            if t in TOPIC_STUDY_NOTES:
                scores[t] = scores.get(t, 0) + g["priority_score"]
                reasons.setdefault(t, []).append(g["skill"])
    ranked = sorted(scores, key=lambda t: -scores[t])[:limit]
    out = [{"topic": t, "priority": round(scores[t], 1), "because": sorted(set(reasons[t]))[:4]} for t in ranked]
    if "hr" not in {o["topic"] for o in out}:
        out.append({"topic": "hr", "priority": 5.0, "because": ["Every role needs behavioural preparation"]})
    return out


def _build_tasks(topics: List[Dict], start: dt.date, weeks: int, hours_per_day: float, skip_topics=()) -> List[Dict]:
    tasks: List[Dict] = []
    days = weeks * 7
    minutes = int(hours_per_day * 60)
    topics = [t for t in topics if t["topic"] not in skip_topics]
    if not topics:
        return tasks
    # study days proportional to priority; Sunday is a lighter mock/revision day
    study_days = [start + dt.timedelta(days=i) for i in range(days) if (start + dt.timedelta(days=i)).weekday() != 6]
    total_p = sum(t["priority"] for t in topics) or 1
    quota = {t["topic"]: max(1, round(len(study_days) * 0.7 * t["priority"] / total_p)) for t in topics}
    order: List[str] = []
    while any(quota.values()):
        for t in topics:
            if quota[t["topic"]] > 0:
                order.append(t["topic"])
                quota[t["topic"]] -= 1
    seen_count: Dict[str, int] = {}
    for day, topic in zip(study_days, order):
        n = seen_count[topic] = seen_count.get(topic, 0) + 1
        week = (day - start).days // 7 + 1
        label = TOPIC_TITLES.get(topic, topic.title())
        kind = "study" if n % 2 == 1 else "practice"
        if kind == "study":
            title, desc = f"Study: {label} (part {(n + 1) // 2})", TOPIC_STUDY_NOTES.get(topic, "")
        else:
            title, desc = f"Practice: {label} questions", ("Answer 3 questions on this topic in the Interview section" +
                                                           (" and solve 1 coding problem." if topic in ("dsa", "sql", "python", "java") else "."))
        tasks.append({"due_date": day, "week_index": week, "topic": topic, "title": title, "description": desc,
                      "task_type": kind, "est_minutes": minutes})
        if kind == "study":
            for off in REVISION_OFFSETS:
                rd = day + dt.timedelta(days=off)
                if rd < start + dt.timedelta(days=days):
                    tasks.append({"due_date": rd, "week_index": (rd - start).days // 7 + 1, "topic": topic,
                                  "title": f"Revise: {label}", "description": f"Spaced revision (+{off} days): recall key points without notes, then check.",
                                  "task_type": "revision", "est_minutes": max(15, minutes // 4)})
    for w in range(weeks):  # weekly mock on Sundays
        sunday = start + dt.timedelta(days=w * 7 + ((6 - start.weekday()) % 7))
        if sunday < start + dt.timedelta(days=days):
            tasks.append({"due_date": sunday, "week_index": w + 1, "topic": "mixed", "title": "Weekly mock interview",
                          "description": "Take an adaptive technical mock and a timed coding assessment; review the feedback.",
                          "task_type": "mock", "est_minutes": minutes})
    tasks.sort(key=lambda t: (t["due_date"], t["task_type"]))
    return tasks


def _weekly_targets(topics: List[Dict], weeks: int) -> List[Dict]:
    out = []
    for w in range(weeks):
        focus = [topics[(w + i) % len(topics)]["topic"] for i in range(min(2, len(topics)))] if topics else []
        out.append({"week": w + 1, "focus_topics": focus,
                    "target": "Complete all study/revision tasks, 1 mock interview, and lift weak-topic scores above 70."})
    return out


def generate(db: Session, user_id: int, weeks: int, hours_per_day: float, role: Optional[str] = None,
             start: Optional[dt.date] = None) -> Roadmap:
    gaps = sg.analyze(db, user_id, role)
    topics = _priority_topics(gaps)
    start = start or dt.date.today()
    db.query(Roadmap).filter(Roadmap.user_id == user_id, Roadmap.status == "active").update({"status": "archived"})
    rm = Roadmap(user_id=user_id, title=f"{gaps['role']} roadmap", target_role=gaps["role"], weeks=weeks,
                 hours_per_day=int(round(hours_per_day)), start_date=start, status="active",
                 weekly_targets=json.dumps(_weekly_targets(topics, weeks)),
                 basis=json.dumps({"role_fit_score": gaps["role_fit_score"], "topics": topics, "hours_per_day": hours_per_day}))
    db.add(rm)
    db.flush()
    for t in _build_tasks(topics, start, weeks, hours_per_day):
        db.add(RoadmapTask(roadmap_id=rm.id, **t))
    db.commit()
    db.refresh(rm)
    return rm


def refresh(db: Session, rm: Roadmap) -> Dict:
    """Dynamic update: re-run the gap analysis, drop remaining tasks for topics now strong, rebuild the rest."""
    gaps = sg.analyze(db, rm.user_id, rm.target_role)
    topics = _priority_topics(gaps)
    strong = {t for g in gaps["gaps"] if g["state"] == "verified_strong" for t in g["topics"]}
    today = max(dt.date.today(), rm.start_date)
    pending = [t for t in rm.tasks if t.status == "todo" and t.due_date >= today]
    for t in pending:
        db.delete(t)
    db.flush()
    remaining_days = (rm.start_date + dt.timedelta(days=rm.weeks * 7) - today).days
    added = 0
    if remaining_days > 0:
        for t in _build_tasks(topics, today, max(1, -(-remaining_days // 7)), rm.hours_per_day, skip_topics=strong):
            if t["due_date"] < rm.start_date + dt.timedelta(days=rm.weeks * 7):
                t["week_index"] = (t["due_date"] - rm.start_date).days // 7 + 1
                db.add(RoadmapTask(roadmap_id=rm.id, **t))
                added += 1
    rm.weekly_targets = json.dumps(_weekly_targets(topics, rm.weeks))
    rm.basis = json.dumps({"role_fit_score": gaps["role_fit_score"], "topics": topics, "hours_per_day": rm.hours_per_day})
    db.commit()
    return {"removed": len(pending), "added": added, "now_strong_topics": sorted(strong), "role_fit_score": gaps["role_fit_score"]}


def progress(rm: Roadmap) -> Dict:
    tasks = rm.tasks
    done = sum(1 for t in tasks if t.status == "done")
    today = dt.date.today()
    overdue = sum(1 for t in tasks if t.status == "todo" and t.due_date < today)
    return {"total": len(tasks), "done": done, "percent": round(100 * done / len(tasks), 1) if tasks else 0.0,
            "overdue": overdue, "due_today": sum(1 for t in tasks if t.status == "todo" and t.due_date == today)}
