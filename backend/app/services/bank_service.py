"""Question-bank seeding and selection helpers."""
import json
import logging

from sqlalchemy.orm import Session

from app.data.question_bank import all_items
from app.models.interview import QuestionBankItem

logger = logging.getLogger("app.bank")


def seed_question_bank(db: Session) -> int:
    """Insert seed questions that are missing (matched by question text). Safe to run on every startup."""
    existing = {q for (q,) in db.query(QuestionBankItem.question).filter(QuestionBankItem.source == "seed")}
    added = 0
    for item in all_items():
        if item["question"] not in existing:
            db.add(QuestionBankItem(**item))
            added += 1
    if added:
        db.commit()
        logger.info("Seeded %d interview bank questions.", added)
    return added


def bank_out(q: QuestionBankItem) -> dict:
    return {"id": q.id, "interview_type": q.interview_type, "topic": q.topic, "difficulty": q.difficulty,
            "question": q.question, "ideal_answer": q.ideal_answer, "key_points": json.loads(q.key_points or "[]"),
            "source": q.source, "is_active": q.is_active}
