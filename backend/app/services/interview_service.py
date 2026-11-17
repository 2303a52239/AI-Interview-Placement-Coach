import json
import datetime as dt
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.ai import usage
from app.ai.factory import get_ai_provider
from app.ai.prompts import RUBRIC_CRITERIA
from app.models.interview import Interview, InterviewQuestion, InterviewAnswer, Evaluation
from app.models.performance import PerformanceSnapshot
from app.models.user import Profile
from app.rag.retriever import CandidateContextRetriever
from app.services import adaptive_engine as eng
from app.services.speech_analysis import analyze_speech

TECH_CRITERIA = ("correctness", "understanding", "completeness", "problem_solving")


def _role(db: Session, user_id: int) -> str:
    p = db.query(Profile).filter(Profile.user_id == user_id).first()
    return (p.target_role if p and p.target_role else "Software Developer")


def _add_question(db: Session, interview: Interview, order: int, text: str, difficulty: str, tag: str,
                  bank_id=None, ideal="", key_points=None, followup_of: Optional[int] = None) -> InterviewQuestion:
    q = InterviewQuestion(interview_id=interview.id, order_index=order, question_text=text, difficulty=difficulty,
                          skill_tag=tag, bank_id=bank_id, ideal_answer=ideal or "",
                          key_points=json.dumps(key_points or []), is_followup=followup_of is not None,
                          parent_question_id=followup_of)
    db.add(q)
    db.flush()
    return q


def _next_from_bank(db: Session, interview: Interview, difficulty: str, history: Dict) -> Optional[InterviewQuestion]:
    topic = eng.choose_topic(db, interview, history)
    item = eng.select_bank_question(db, interview, topic, difficulty)
    if item is None and interview.interview_type == "technical":
        # topic exhausted: try any other topic
        for t in eng.TECH_TOPICS:
            item = eng.select_bank_question(db, interview, t, difficulty)
            if item:
                topic = t
                break
    if item is None:
        return None
    role = interview.target_role or "Software Developer"
    return _add_question(db, interview, len(interview.questions), item.question.replace("{role}", role),
                         item.difficulty, item.topic, item.id, item.ideal_answer, json.loads(item.key_points or "[]"))


def start_interview(db: Session, user_id: int, interview_type: str, num_questions: int,
                    topic: str = "mixed", adaptive: bool = False, voice_mode: bool = False) -> Interview:
    provider = get_ai_provider()
    role = _role(db, user_id)
    history = eng.topic_history(db, user_id)
    interview = Interview(user_id=user_id, interview_type=interview_type, target_role=role, status="in_progress",
                          started_at=dt.datetime.utcnow(), topic=topic if interview_type == "technical" else "hr",
                          adaptive=adaptive, target_questions=num_questions, voice_mode=voice_mode,
                          simulated=bool(provider.simulated))
    ref_topic = interview.topic if interview.topic != "mixed" else "mixed"
    interview.current_difficulty = eng.start_difficulty(history, ref_topic) if ref_topic != "mixed" else "easy"
    db.add(interview)
    db.flush()
    db.refresh(interview)

    # adaptive: only the first question now; others are chosen after each answer.
    # fixed: the whole set up front, on an easy -> medium -> hard ladder.
    count = 1 if adaptive else num_questions
    ladder = ["easy", "medium", "medium", "hard", "hard"]
    for i in range(count):
        diff = interview.current_difficulty if adaptive else ladder[min(i, len(ladder) - 1)] if num_questions > 2 else "medium"
        q = _next_from_bank(db, interview, diff, history)
        if q is None:  # bank exhausted -> ask the provider (LLM or mock generator)
            ctx = CandidateContextRetriever(db, user_id).get_context(f"{interview_type} interview for {role}")
            gen = provider.generate_questions(interview_type, role, ctx, 1)
            item = gen[0]
            _add_question(db, interview, len(interview.questions), item["question"], item.get("difficulty", "medium"),
                          item.get("skill_tag", "general"), None, item.get("ideal_answer", ""), [])
        db.refresh(interview)
    usage.persist(db, user_id)
    db.commit()
    db.refresh(interview)
    return interview


def submit_answer(db: Session, interview: Interview, question: InterviewQuestion, answer_text: str,
                  input_mode: str, duration_seconds: Optional[float] = None, pauses: Optional[List[float]] = None
                  ) -> Tuple[InterviewAnswer, Evaluation, Optional[InterviewQuestion]]:
    provider = get_ai_provider()
    result = provider.evaluate_rubric(interview.interview_type, question.skill_tag, question.question_text,
                                      answer_text, question.ideal_answer or "", json.loads(question.key_points or "[]"))
    speech = None
    if input_mode == "voice":
        speech = analyze_speech(answer_text, duration_seconds, pauses)
    answer = InterviewAnswer(question_id=question.id, answer_text=answer_text, input_mode=input_mode,
                             submitted_at=dt.datetime.utcnow(), speech_metrics=json.dumps(speech) if speech else "")
    db.add(answer)
    db.flush()
    evaluation = Evaluation(
        answer_id=answer.id, score=result["score"], strengths=json.dumps(result.get("strengths", [])),
        weaknesses=json.dumps(result.get("weaknesses", [])), feedback=result.get("feedback", ""),
        suggested_improvement=result.get("suggested_improvement", ""), rubric=json.dumps(result.get("rubric", {})),
        ideal_answer=result.get("ideal_answer", ""), missing_points=json.dumps(result.get("missing_points", [])),
        provider=result.get("provider", "mock"), simulated=bool(result.get("simulated", True)))
    db.add(evaluation)
    db.flush()
    db.refresh(interview)

    next_q: Optional[InterviewQuestion] = None
    if interview.adaptive:
        next_q = _choose_next(db, interview, question, result, provider)
    usage.persist(db, interview.user_id)
    db.commit()
    db.refresh(evaluation)
    if next_q is not None:
        db.refresh(next_q)
    return answer, evaluation, next_q


def _choose_next(db, interview: Interview, question: InterviewQuestion, result: Dict, provider) -> Optional[InterviewQuestion]:
    score = float(result["score"])
    interview.current_difficulty = eng.next_difficulty(interview.current_difficulty, score)
    answered_main = sum(1 for q in interview.questions if not q.is_followup and q.answer is not None) + \
        (0 if question.is_followup or question.answer is not None else 1)
    missing = result.get("missing_points", [])
    if eng.should_follow_up(score, missing, interview, question) and answered_main <= interview.target_questions:
        fu = provider.generate_followup(interview.interview_type, question.question_text, "", missing)
        if fu:
            return _add_question(db, interview, len(interview.questions), fu["question"], question.difficulty,
                                 question.skill_tag, None, fu.get("ideal_answer", ""), fu.get("key_points", []), question.id)
    if answered_main >= interview.target_questions:
        return None
    history = eng.topic_history(db, interview.user_id)
    return _next_from_bank(db, interview, interview.current_difficulty, history)


def _avg(xs: List[float]) -> float:
    return round(sum(xs) / len(xs), 1) if xs else 0.0


def complete_interview(db: Session, interview: Interview) -> Interview:
    rows = []
    for q in interview.questions:
        if q.answer and q.answer.evaluation:
            ev = q.answer.evaluation
            rows.append((q, ev, json.loads(ev.rubric or "{}")))
    interview.status = "completed"
    interview.completed_at = dt.datetime.utcnow()
    interview.duration_seconds = int((interview.completed_at - interview.started_at).total_seconds())

    if not rows:
        interview.overall_score = interview.technical_score = interview.communication_score = None
        interview.strengths = "[]"
        interview.weaknesses = json.dumps(["No questions were answered."])
        interview.ai_feedback = "No answers were submitted, so this round was not scored and won't affect your analytics."
        interview.recommended_topics = "[]"
        db.add(interview)
        db.commit()
        db.refresh(interview)
        return interview

    overall = _avg([ev.score for _, ev, _ in rows])
    crit_avg: Dict[str, float] = {}
    for c in RUBRIC_CRITERIA:
        vals = [float(r[c]["score"]) for _, _, r in rows if c in r]
        if vals:
            crit_avg[c] = _avg(vals)
    tech = _avg([crit_avg[c] for c in TECH_CRITERIA if c in crit_avg]) or overall
    comm = crit_avg.get("communication", overall)

    topic_scores: Dict[str, List[float]] = {}
    for q, ev, _ in rows:
        topic_scores.setdefault(q.skill_tag, []).append(ev.score)
    topic_avg = {t: _avg(v) for t, v in topic_scores.items()}

    strengths = [f"Strong {c.replace('_', ' ')} ({v:.0f}/100)." for c, v in crit_avg.items() if v >= 70]
    weaknesses = [f"Improve {c.replace('_', ' ')} ({v:.0f}/100)." for c, v in crit_avg.items() if v < 55]
    strengths += [f"Good command of {t.replace('_', ' ')} ({v:.0f})." for t, v in topic_avg.items() if v >= 70]
    weaknesses += [f"Weak on {t.replace('_', ' ')} ({v:.0f})." for t, v in topic_avg.items() if v < 55]
    recommended = [t for t, v in sorted(topic_avg.items(), key=lambda kv: kv[1]) if v < 70][:4]
    if not recommended and interview.interview_type == "hr":
        recommended = [c for c, v in sorted(crit_avg.items(), key=lambda kv: kv[1])[:2]]

    if overall >= 75:
        fb = f"Strong round: {overall:.0f}/100 across {len(rows)} answers."
    elif overall >= 55:
        fb = f"A decent round at {overall:.0f}/100. Focus on the topics and criteria listed below to lift your score."
    else:
        fb = f"This round scored {overall:.0f}/100. Review the ideal answers in the detailed feedback and retry the weak topics."
    if interview.simulated:
        fb += " (Scored by the built-in rule-based evaluator, not a language model.)"

    interview.overall_score, interview.technical_score, interview.communication_score = overall, tech, comm
    interview.strengths = json.dumps(strengths[:6])
    interview.weaknesses = json.dumps(weaknesses[:6])
    interview.ai_feedback = fb
    interview.recommended_topics = json.dumps(recommended)
    db.add(interview)
    db.add(PerformanceSnapshot(user_id=interview.user_id, source_type=interview.interview_type, source_id=interview.id,
                               score=overall, difficulty="mixed",
                               skill_tags=json.dumps(sorted({q.skill_tag for q, _, _ in rows}))))
    db.commit()
    db.refresh(interview)
    return interview
