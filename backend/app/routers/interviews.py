import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.interview import Interview, InterviewQuestion
from app.schemas.interview import (
    StartInterviewRequest, InterviewStartResponse, QuestionOut,
    SubmitAnswerRequest, SubmitAnswerResponse, EvaluationOut,
    InterviewCompleteResponse, InterviewHistoryItem, InterviewDetailResponse, InterviewDetailQuestion,
)
from app.utils.security import get_current_user
from app.data.question_bank import TECH_TOPICS
from app.services.interview_service import start_interview, submit_answer, complete_interview

router = APIRouter(prefix="/interviews", tags=["Interviews"])


def _get_owned_interview(db: Session, interview_id: int, user_id: int) -> Interview:
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview or interview.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found.")
    return interview


def _evaluation_out(ev, answer=None) -> EvaluationOut:
    return EvaluationOut(
        score=ev.score, strengths=json.loads(ev.strengths or "[]"), weaknesses=json.loads(ev.weaknesses or "[]"),
        feedback=ev.feedback, suggested_improvement=ev.suggested_improvement,
        rubric=json.loads(ev.rubric or "{}"), ideal_answer=ev.ideal_answer or "",
        missing_points=json.loads(ev.missing_points or "[]"), simulated=ev.simulated,
        speech=json.loads(answer.speech_metrics) if answer is not None and answer.speech_metrics else None)


@router.post("/start", response_model=InterviewStartResponse)
def start(payload: StartInterviewRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.interview_type not in ("hr", "technical"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="interview_type must be 'hr' or 'technical'.")
    if not (1 <= payload.num_questions <= 30):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="num_questions must be between 1 and 30.")

    if payload.interview_type == "technical" and payload.topic != "mixed" and payload.topic not in TECH_TOPICS:
        raise HTTPException(status_code=400, detail=f"Unknown topic. Use one of: mixed, {', '.join(TECH_TOPICS)}.")
    interview = start_interview(db, current_user.id, payload.interview_type, payload.num_questions,
                                payload.topic, payload.adaptive, payload.voice_mode)
    questions = [QuestionOut.model_validate(q) for q in sorted(interview.questions, key=lambda q: q.order_index)]
    return InterviewStartResponse(
        interview_id=interview.id,
        interview_type=interview.interview_type,
        target_role=interview.target_role,
        questions=questions, adaptive=interview.adaptive, target_questions=interview.target_questions,
        topic=interview.topic, simulated=interview.simulated,
    )


@router.post("/{interview_id}/answer", response_model=SubmitAnswerResponse)
def answer(interview_id: int, payload: SubmitAnswerRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    interview = _get_owned_interview(db, interview_id, current_user.id)
    if interview.status == "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This interview has already been completed.")

    question = db.query(InterviewQuestion).filter(
        InterviewQuestion.id == payload.question_id, InterviewQuestion.interview_id == interview.id
    ).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found for this interview.")
    if question.answer is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This question has already been answered.")

    answer_row, evaluation, adaptive_next = submit_answer(
        db, interview, question, payload.answer_text, payload.input_mode, payload.duration_seconds, payload.pauses)

    db.refresh(interview)
    if interview.adaptive:
        next_question = QuestionOut.model_validate(adaptive_next) if adaptive_next else None
    else:
        remaining = [q for q in sorted(interview.questions, key=lambda q: q.order_index) if q.answer is None]
        next_question = QuestionOut.model_validate(remaining[0]) if remaining else None

    return SubmitAnswerResponse(
        question_id=question.id,
        evaluation=_evaluation_out(evaluation, answer_row),
        next_question=next_question,
        current_difficulty=interview.current_difficulty,
    )


@router.post("/{interview_id}/complete", response_model=InterviewCompleteResponse)
def complete(interview_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    interview = _get_owned_interview(db, interview_id, current_user.id)
    if interview.status == "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This interview has already been completed.")

    interview = complete_interview(db, interview)
    return InterviewCompleteResponse(
        interview_id=interview.id,
        overall_score=interview.overall_score or 0.0,
        technical_score=interview.technical_score or 0.0,
        communication_score=interview.communication_score or 0.0,
        strengths=json.loads(interview.strengths or "[]"),
        weaknesses=json.loads(interview.weaknesses or "[]"),
        ai_feedback=interview.ai_feedback,
        recommended_topics=json.loads(interview.recommended_topics or "[]"),
    )


@router.get("/history", response_model=list[InterviewHistoryItem])
def history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    interviews = (
        db.query(Interview)
        .filter(Interview.user_id == current_user.id)
        .order_by(Interview.started_at.desc())
        .all()
    )
    items = []
    for i in interviews:
        difficulties = sorted({q.difficulty for q in i.questions})
        items.append(InterviewHistoryItem(
            id=i.id, interview_type=i.interview_type, status=i.status, overall_score=i.overall_score,
            started_at=i.started_at, completed_at=i.completed_at, duration_seconds=i.duration_seconds,
            difficulty=difficulties[0] if len(difficulties) == 1 else ("mixed" if difficulties else "n/a"),
            strengths=json.loads(i.strengths or "[]")[:3],
            weaknesses=json.loads(i.weaknesses or "[]")[:3],
        ))
    return items


@router.get("/{interview_id}", response_model=InterviewDetailResponse)
def detail(interview_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    interview = _get_owned_interview(db, interview_id, current_user.id)
    questions = []
    for q in sorted(interview.questions, key=lambda q: q.order_index):
        answer_text = q.answer.answer_text if q.answer else None
        score = q.answer.evaluation.score if (q.answer and q.answer.evaluation) else None
        feedback = q.answer.evaluation.feedback if (q.answer and q.answer.evaluation) else None
        ev = q.answer.evaluation if (q.answer and q.answer.evaluation) else None
        questions.append(InterviewDetailQuestion(
            question_text=q.question_text, difficulty=q.difficulty, skill_tag=q.skill_tag,
            answer_text=answer_text, score=score, feedback=feedback,
            rubric=json.loads(ev.rubric or "{}") if ev else {}, ideal_answer=(ev.ideal_answer if ev else "") or "",
            missing_points=json.loads(ev.missing_points or "[]") if ev else [], is_followup=q.is_followup,
            speech=json.loads(q.answer.speech_metrics) if (q.answer and q.answer.speech_metrics) else None,
        ))

    return InterviewDetailResponse(
        id=interview.id,
        interview_type=interview.interview_type,
        status=interview.status,
        overall_score=interview.overall_score,
        technical_score=interview.technical_score,
        communication_score=interview.communication_score,
        strengths=json.loads(interview.strengths or "[]"),
        weaknesses=json.loads(interview.weaknesses or "[]"),
        ai_feedback=interview.ai_feedback,
        recommended_topics=json.loads(interview.recommended_topics or "[]"),
        started_at=interview.started_at,
        completed_at=interview.completed_at,
        questions=questions, topic=interview.topic, adaptive=interview.adaptive, simulated=interview.simulated,
    )
