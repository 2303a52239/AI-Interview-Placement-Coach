"""Adaptive question selection: difficulty ladder, history-based personalisation, follow-ups."""
import json
import random
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.data.question_bank import TECH_TOPICS
from app.models.interview import (
    Interview, InterviewQuestion, InterviewAnswer, Evaluation, QuestionBankItem,
)
from app.models.resume import Resume
from app.data.skills import find_skills

LEVELS = ["easy", "medium", "hard"]
TOPIC_FROM_SKILL = {"python": "python", "java": "java", "sql": "sql", "postgresql": "sql", "mysql": "sql",
                    "data structures": "dsa", "algorithms": "dsa", "dbms": "dbms", "operating systems": "os",
                    "computer networks": "cn", "machine learning": "ml", "deep learning": "dl", "nlp": "nlp",
                    "generative ai": "genai", "llms": "llm", "rag": "rag", "system design": "system_design"}


def topic_history(db: Session, user_id: int) -> Dict[str, Dict[str, float]]:
    """Average evaluation score and attempts per topic for this user, from real stored evaluations."""
    rows = (db.query(InterviewQuestion.skill_tag, func.avg(Evaluation.score), func.count(Evaluation.id))
            .join(InterviewAnswer, InterviewAnswer.question_id == InterviewQuestion.id)
            .join(Evaluation, Evaluation.answer_id == InterviewAnswer.id)
            .join(Interview, Interview.id == InterviewQuestion.interview_id)
            .filter(Interview.user_id == user_id)
            .group_by(InterviewQuestion.skill_tag).all())
    return {tag: {"avg": float(avg), "attempts": int(n)} for tag, avg, n in rows}


def start_difficulty(history: Dict[str, Dict[str, float]], topic: str) -> str:
    h = history.get(topic)
    if not h or h["attempts"] < 2:
        return "easy" if not h else "medium"
    return "hard" if h["avg"] >= 80 else "medium" if h["avg"] >= 55 else "easy"


def next_difficulty(current: str, last_score: Optional[float]) -> str:
    i = LEVELS.index(current) if current in LEVELS else 1
    if last_score is None:
        return current
    if last_score >= 75:
        i = min(2, i + 1)
    elif last_score < 45:
        i = max(0, i - 1)
    return LEVELS[i]


def _resume_topics(db: Session, user_id: int) -> List[str]:
    r = db.query(Resume).filter(Resume.user_id == user_id, Resume.is_active == True).first()  # noqa: E712
    if not r:
        return []
    tops = []
    for s in find_skills(r.raw_text or ""):
        t = TOPIC_FROM_SKILL.get(s.lower())
        if t and t not in tops:
            tops.append(t)
    return tops


def choose_topic(db: Session, interview: Interview, history: Dict) -> str:
    """For 'mixed' technical interviews: rotate through topics, favouring weak topics then resume-relevant ones."""
    if interview.interview_type == "hr":
        return "hr"
    if interview.topic and interview.topic != "mixed":
        return interview.topic
    asked = [q.skill_tag for q in interview.questions if not q.is_followup]
    candidates = [t for t in TECH_TOPICS]
    weak = sorted([t for t in candidates if t in history and history[t]["avg"] < 65], key=lambda t: history[t]["avg"])
    resume = [t for t in _resume_topics(db, interview.user_id) if t in candidates]
    fresh = [t for t in candidates if t not in history]
    order = weak + [t for t in resume if t not in weak] + [t for t in fresh if t not in weak and t not in resume] + candidates
    seen = []
    for t in order:
        if t not in seen:
            seen.append(t)
    for t in seen:
        if t not in asked:
            return t
    return seen[len(asked) % len(seen)]


def select_bank_question(db: Session, interview: Interview, topic: str, difficulty: str,
                         rng: Optional[random.Random] = None) -> Optional[QuestionBankItem]:
    rng = rng or random.Random()
    used_in_this = {q.bank_id for q in interview.questions if q.bank_id}
    recent = {bid for (bid,) in db.query(InterviewQuestion.bank_id)
              .join(Interview, Interview.id == InterviewQuestion.interview_id)
              .filter(Interview.user_id == interview.user_id, InterviewQuestion.bank_id.isnot(None)).all()}
    base = db.query(QuestionBankItem).filter(QuestionBankItem.interview_type == interview.interview_type,
                                             QuestionBankItem.is_active == True)  # noqa: E712
    if interview.interview_type == "technical":
        base = base.filter(QuestionBankItem.topic == topic)
    pool = [q for q in base.all() if q.id not in used_in_this]
    if not pool:
        return None
    # prefer: exact difficulty not seen by the user before -> exact difficulty -> nearest difficulty -> anything
    for allow_seen in (False, True):
        for d in sorted(LEVELS, key=lambda x: abs(LEVELS.index(x) - LEVELS.index(difficulty))):
            pick = [q for q in pool if q.difficulty == d and (allow_seen or q.id not in recent)]
            if pick:
                return rng.choice(pick)
    return rng.choice(pool)


def should_follow_up(score: float, missing: List[str], interview: Interview, parent: InterviewQuestion) -> bool:
    if parent.is_followup or score >= 50 or not missing:
        return False
    followups = sum(1 for q in interview.questions if q.is_followup)
    return followups < 2
