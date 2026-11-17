import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.coding.executor import LANGUAGES
from app.database import get_db
from app.models.coding import CodingQuestion, CodingSubmission, CodingAssessment
from app.models.user import User
from app.schemas.coding import (
    CodingQuestionOut, CodeSubmitRequest, CodeSubmitResponse, TestCaseResult, CodeRunResponse,
    SubmissionListItem, SubmissionDetail, AssessmentStart, AssessmentOut,
)
from app.services import coding_service as cs
from app.utils.pagination import PageParams, paginate
from app.utils.security import get_current_user

router = APIRouter(prefix="/coding", tags=["Coding Assessment"])


def _question(db: Session, qid: int) -> CodingQuestion:
    q = db.query(CodingQuestion).filter(CodingQuestion.id == qid).first()
    if not q:
        raise HTTPException(status_code=404, detail="Coding question not found.")
    return q


@router.get("/languages")
def languages():
    return {"languages": list(LANGUAGES)}


@router.get("/questions", response_model=list[CodingQuestionOut])
def list_questions(difficulty: Optional[str] = None, topic: Optional[str] = None, company: Optional[str] = None,
                   db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(CodingQuestion)
    if difficulty:
        query = query.filter(CodingQuestion.difficulty == difficulty)
    if topic:
        query = query.filter(CodingQuestion.topic_tag == topic)
    rows = query.order_by(CodingQuestion.id).all()
    if company:
        rows = [r for r in rows if company.lower() in [c.lower() for c in json.loads(r.company_tags or "[]")]]
    return [CodingQuestionOut(**cs.question_out(q)) for q in rows]


@router.get("/questions/{question_id}", response_model=CodingQuestionOut)
def get_question(question_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return CodingQuestionOut(**cs.question_out(_question(db, question_id)))


@router.post("/submit", response_model=CodeSubmitResponse)
def submit(payload: CodeSubmitRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    question = _question(db, payload.question_id)
    if not payload.source_code.strip():
        raise HTTPException(status_code=400, detail="Source code cannot be empty.")
    sub, cases, est = cs.submit_code(db, current_user.id, question, payload.source_code, payload.language, payload.assessment_id)
    return CodeSubmitResponse(
        submission_id=sub.id, status=sub.status, language=sub.language, compile_output=sub.compile_output,
        passed_test_cases=sub.passed_test_cases, total_test_cases=sub.total_test_cases,
        hidden_passed=sub.hidden_passed, hidden_total=sub.hidden_total, execution_time_ms=sub.execution_time_ms,
        time_complexity_estimate=sub.time_complexity_estimate, space_complexity_estimate=sub.space_complexity_estimate,
        complexity_note=est["note"], score=sub.score, ai_feedback=sub.ai_feedback, sandbox=sub.sandbox,
        test_case_results=[TestCaseResult(**c) for c in cases])


@router.post("/run", response_model=CodeRunResponse)
def run_sample(payload: CodeSubmitRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Run against the SAMPLE input only. Nothing is saved or scored (the 'Run' button)."""
    question = _question(db, payload.question_id)
    if not payload.source_code.strip():
        raise HTTPException(status_code=400, detail="Source code cannot be empty.")
    result = cs.run_sample(question, payload.source_code, payload.language)
    first = result.cases[0] if result.cases else None
    return CodeRunResponse(
        status=result.status, compile_output=result.compile_output, sample_input=question.sample_input,
        expected_output=question.sample_output, actual_output=first.actual_output if first else "",
        passed=bool(first and first.passed), execution_time_ms=result.execution_time_ms,
        language=payload.language, sandbox=result.sandbox)


# ---------------------------------------------------------------- submission history
@router.get("/submissions")
def submissions(question_id: Optional[int] = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(CodingSubmission, CodingQuestion.title).join(CodingQuestion, CodingQuestion.id == CodingSubmission.question_id) \
        .filter(CodingSubmission.user_id == current_user.id)
    if question_id:
        q = q.filter(CodingSubmission.question_id == question_id)
    q = q.order_by(CodingSubmission.submitted_at.desc(), CodingSubmission.id.desc())
    return paginate(q, PageParams(page=page, page_size=page_size), lambda r: SubmissionListItem(
        id=r[0].id, question_id=r[0].question_id, question_title=r[1], language=r[0].language, status=r[0].status,
        score=r[0].score, passed_test_cases=r[0].passed_test_cases, total_test_cases=r[0].total_test_cases,
        execution_time_ms=r[0].execution_time_ms, submitted_at=r[0].submitted_at).model_dump())


@router.get("/submissions/{submission_id}", response_model=SubmissionDetail)
def submission_detail(submission_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(CodingSubmission, CodingQuestion.title).join(CodingQuestion, CodingQuestion.id == CodingSubmission.question_id) \
        .filter(CodingSubmission.id == submission_id, CodingSubmission.user_id == current_user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found.")
    s, title = row
    return SubmissionDetail(
        id=s.id, question_id=s.question_id, question_title=title, language=s.language, status=s.status, score=s.score,
        passed_test_cases=s.passed_test_cases, total_test_cases=s.total_test_cases, execution_time_ms=s.execution_time_ms,
        submitted_at=s.submitted_at, source_code=s.source_code, compile_output=s.compile_output, ai_feedback=s.ai_feedback,
        time_complexity_estimate=s.time_complexity_estimate, space_complexity_estimate=s.space_complexity_estimate)


# ---------------------------------------------------------------- timed assessments
def _owned_assessment(db, user, aid) -> CodingAssessment:
    a = db.query(CodingAssessment).filter(CodingAssessment.id == aid, CodingAssessment.user_id == user.id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found.")
    return a


@router.post("/assessments", response_model=AssessmentOut, status_code=status.HTTP_201_CREATED)
def start_assessment(payload: AssessmentStart, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = cs.start_assessment(db, current_user.id, payload.num_questions, payload.duration_minutes, payload.difficulty, payload.company)
    return AssessmentOut(**cs.assessment_out(db, a))


@router.get("/assessments", response_model=list[AssessmentOut])
def list_assessments(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(CodingAssessment).filter(CodingAssessment.user_id == current_user.id) \
        .order_by(CodingAssessment.started_at.desc()).limit(20).all()
    return [AssessmentOut(**cs.assessment_out(db, a)) for a in rows]


@router.get("/assessments/{assessment_id}", response_model=AssessmentOut)
def get_assessment(assessment_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AssessmentOut(**cs.assessment_out(db, _owned_assessment(db, current_user, assessment_id)))


@router.post("/assessments/{assessment_id}/finish", response_model=AssessmentOut)
def finish_assessment(assessment_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = _owned_assessment(db, current_user, assessment_id)
    cs.refresh_assessment_status(db, a)
    if a.status == "in_progress":
        cs.finalize(db, a, "completed")
    return AssessmentOut(**cs.assessment_out(db, a))
