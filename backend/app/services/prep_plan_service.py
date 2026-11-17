"""
Recommendation engine that turns weak-topic performance data into a
concrete, prioritized preparation plan. Regenerated (replacing the previous
plan) whenever new interview/coding results come in, or on demand.
"""
import json
import datetime as dt
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.performance import PerformanceSnapshot, PreparationPlan, PreparationItem

TOPIC_RECOMMENDATIONS = {
    "java": ("Practice core Java: OOP concepts, exception handling, and Collections (HashMap, HashSet, ArrayList).", "Solve 10 Java practice problems on collections and OOP design."),
    "python": ("Revise Python fundamentals: list/dict comprehensions, decorators, and OOP.", "Solve 10 Python problems focused on data structures and functions."),
    "react": ("Deepen React hooks understanding: useState, useEffect, useContext, and component design.", "Build a small CRUD app using React hooks to reinforce concepts."),
    "javascript": ("Review JavaScript fundamentals: closures, async/await, and the event loop.", "Solve JS output-prediction quizzes and small coding challenges."),
    "sql": ("Practice SQL joins, indexing, and normalization concepts.", "Write 10 SQL queries covering joins, aggregations, and subqueries."),
    "data structures": ("Revisit core data structures: arrays, linked lists, trees, and hash tables.", "Implement each data structure from scratch and solve 5 related problems."),
    "algorithms": ("Strengthen algorithmic thinking: sorting, searching, recursion, and complexity analysis.", "Solve medium-difficulty problems on arrays and recursion daily."),
    "machine learning": ("Review core ML concepts: bias-variance tradeoff, overfitting, and evaluation metrics.", "Work through 2-3 applied ML mini-projects with scikit-learn."),
    "data analysis": ("Practice data cleaning and exploratory analysis techniques.", "Analyze a public dataset end-to-end with pandas and visualize insights."),
    "communication": ("Practice structuring answers with the STAR method (Situation, Task, Action, Result).", "Record yourself answering 3 common HR questions and review clarity."),
    "self_awareness": ("Prepare concrete, specific examples for strengths/weaknesses questions.", "Write out 3 strength and 3 weakness stories with measurable outcomes."),
    "motivation": ("Research target companies/roles deeply to give specific, genuine answers.", "Draft tailored 'why this company/role' answers for 2 target companies."),
    "teamwork": ("Prepare examples of conflict resolution and collaboration.", "Write 2 STAR stories about resolving team disagreements."),
    "general": ("Do a broad review across your weakest scoring areas.", "Take one more mock interview this week to measure improvement."),
}

DEFAULT_RECOMMENDATION = ("Review fundamentals related to this topic and practice sample questions.", "Practice 5-10 questions on this topic this week.")


def generate_preparation_plan(db: Session, user_id: int) -> PreparationPlan:
    snapshots = db.query(PerformanceSnapshot).filter(PerformanceSnapshot.user_id == user_id).all()

    skill_scores = defaultdict(list)
    for s in snapshots:
        try:
            tags = json.loads(s.skill_tags or "[]")
        except json.JSONDecodeError:
            tags = []
        for tag in tags:
            skill_scores[tag].append(s.score)

    def avg(scores):
        return sum(scores) / len(scores) if scores else 0

    ranked = sorted(skill_scores.items(), key=lambda kv: avg(kv[1]))

    # remove any previous plan for this user (regenerate fresh each time)
    old_plan = db.query(PreparationPlan).filter(PreparationPlan.user_id == user_id).first()
    if old_plan:
        db.delete(old_plan)
        db.flush()

    plan = PreparationPlan(user_id=user_id, generated_at=dt.datetime.utcnow())
    db.add(plan)
    db.flush()

    if not ranked:
        item = PreparationItem(
            plan_id=plan.id,
            topic="Getting Started",
            priority="high",
            recommendation="Take your first HR or Technical mock interview to generate a personalized plan.",
            suggested_practice="Complete at least one interview or coding assessment.",
            schedule="Today",
        )
        db.add(item)
        db.commit()
        db.refresh(plan)
        return plan

    for idx, (topic, scores) in enumerate(ranked[:6]):
        average = avg(scores)
        if average < 60:
            priority, schedule = "high", "This week"
        elif average < 75:
            priority, schedule = "medium", "Next 2 weeks"
        else:
            priority, schedule = "low", "Ongoing / maintenance"

        recommendation, practice = TOPIC_RECOMMENDATIONS.get(topic, DEFAULT_RECOMMENDATION)

        item = PreparationItem(
            plan_id=plan.id,
            topic=topic.replace("_", " ").title(),
            priority=priority,
            recommendation=recommendation,
            suggested_practice=practice,
            schedule=schedule,
        )
        db.add(item)

    db.commit()
    db.refresh(plan)
    return plan


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def build_weekly_schedule(items) -> list[dict]:
    """Turns the prioritized items into a 7-day plan: high-priority topics get
    more days; Saturday is a mock interview; Sunday is review."""
    ordered = sorted(items, key=lambda i: {"high": 0, "medium": 1, "low": 2}.get(i.priority, 3))
    if not ordered:
        return []
    weights = []
    for item in ordered:
        weights.extend([item] * {"high": 3, "medium": 2, "low": 1}.get(item.priority, 1))
    schedule = []
    for idx, day in enumerate(DAYS[:5]):
        item = weights[idx % len(weights)]
        schedule.append({"day": day, "focus": item.topic, "activity": item.suggested_practice})
    schedule.append({"day": "Saturday", "focus": "Full mock interview",
                     "activity": "Take one HR or technical round and one coding problem under timed conditions."})
    schedule.append({"day": "Sunday", "focus": "Review & rest",
                     "activity": "Re-read feedback from this week's attempts and note three things to improve."})
    return schedule
