import datetime as dt
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.coding import CodingQuestion
from app.models.interview import Interview
from typing import List, Optional
from fastapi import Query
from fastapi.responses import Response
from pydantic import Field
from app.models.interview import QuestionBankItem
from app.models.coding import CodingAssessment, CodingSubmission
from app.models.resume import JobDescription
from app.models.user import Profile
from app.data.question_bank import TECH_TOPICS
from app.data.skills import find_skills
from app.services import admin_service as adm
from app.services import profile_service as ps
from app.services.bank_service import bank_out
from app.utils.pagination import PageParams, paginate
from app.utils.security import get_current_admin, get_staff_user
from app.coding.executor import LANGUAGES

router = APIRouter(prefix="/admin", tags=["Admin"])


class CodingQuestionCreate(BaseModel):
    title: str
    problem_statement: str
    input_format: str = ""
    output_format: str = ""
    constraints: str = ""
    sample_input: str = ""
    sample_output: str = ""
    difficulty: str = "easy"
    topic_tag: str = "general"
    starter_code: str = ""
    starter_codes: dict = {}
    time_limit_seconds: int = Field(default=0, ge=0, le=60)
    company_tags: list[str] = []
    test_cases: list[dict]  # [{"input": "...", "expected_output": "...", "hidden": bool}]


class CandidateOverview(BaseModel):
    user_id: int
    name: str
    email: str
    total_interviews: int
    average_score: float


@router.get("/coding-questions")
def list_all_coding_questions(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return db.query(CodingQuestion).all()


@router.post("/coding-questions", status_code=status.HTTP_201_CREATED)
def create_coding_question(payload: CodingQuestionCreate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    if not payload.test_cases:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one test case is required.")
    question = CodingQuestion(
        title=payload.title,
        problem_statement=payload.problem_statement,
        input_format=payload.input_format,
        output_format=payload.output_format,
        constraints=payload.constraints,
        sample_input=payload.sample_input,
        sample_output=payload.sample_output,
        difficulty=payload.difficulty,
        topic_tag=payload.topic_tag,
        starter_code=payload.starter_code, starter_codes=json.dumps(payload.starter_codes),
        time_limit_seconds=payload.time_limit_seconds, company_tags=json.dumps(payload.company_tags),
        test_cases=json.dumps(payload.test_cases),
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@router.post("/coding-questions/import")
def import_coding_questions(items: List[dict], db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """Bulk-add problems from a JSON list (format: app/services/coding_import.py). Existing titles are skipped."""
    from app.services.coding_import import import_questions
    try:
        return import_questions(db, items)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/coding-questions/{question_id}")
def update_coding_question(question_id: int, payload: CodingQuestionCreate, db: Session = Depends(get_db),
                           admin: User = Depends(get_current_admin)):
    q = db.query(CodingQuestion).filter(CodingQuestion.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found.")
    if not payload.test_cases:
        raise HTTPException(status_code=400, detail="At least one test case is required.")
    for f in ("title", "problem_statement", "input_format", "output_format", "constraints", "sample_input",
              "sample_output", "difficulty", "topic_tag", "starter_code", "time_limit_seconds"):
        setattr(q, f, getattr(payload, f))
    q.starter_codes, q.company_tags, q.test_cases = json.dumps(payload.starter_codes), json.dumps(payload.company_tags), json.dumps(payload.test_cases)
    db.commit()
    return {"id": q.id}


@router.delete("/coding-questions/{question_id}")
def delete_coding_question(question_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    question = db.query(CodingQuestion).filter(CodingQuestion.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")
    db.delete(question)
    db.commit()
    return {"message": "Deleted."}


@router.get("/candidates", response_model=list[CandidateOverview])
def list_candidates(db: Session = Depends(get_db), admin: User = Depends(get_staff_user)):
    users = db.query(User).filter(User.role == "student").all()
    overview = []
    for u in users:
        interviews = db.query(Interview).filter(Interview.user_id == u.id, Interview.status == "completed").all()
        scores = [i.overall_score for i in interviews if i.overall_score is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
        overview.append(CandidateOverview(user_id=u.id, name=u.name, email=u.email,
                                           total_interviews=len(interviews), average_score=avg_score))
    return overview


# ----------------------------------------------------------------------------- students (staff: read-only)
@router.get("/students")
def students(search: Optional[str] = None, branch: Optional[str] = None, graduation_year: Optional[int] = None,
             page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
             db: Session = Depends(get_db), staff: User = Depends(get_staff_user)):
    q = adm.student_query(db, search, branch, graduation_year)
    return paginate(q, PageParams(page=page, page_size=page_size), lambda r: adm.student_row(db, r[0], r[1]))


@router.get("/students/{user_id}")
def student_detail(user_id: int, db: Session = Depends(get_db), staff: User = Depends(get_staff_user)):
    u = db.query(User).filter(User.id == user_id, User.role == "student").first()
    if not u:
        raise HTTPException(status_code=404, detail="Student not found.")
    from app.services.analytics_service import student_analytics
    a = student_analytics(db, u.id)
    return {"summary": adm.student_row(db, u, db.query(Profile).filter(Profile.user_id == u.id).first()),
            "profile": ps.build_profile_out(db, u).model_dump(), "readiness": ps.readiness(db, u),
            "overview": a["overview"], "topics": a["topics"], "trend": a["trend"], "rubric": a["rubric"]}


class UserUpdate(BaseModel):
    role: Optional[str] = Field(default=None, pattern="^(student|placement_officer|admin)$")
    is_active: Optional[bool] = None


@router.patch("/users/{user_id}")
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found.")
    if u.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot change your own role or deactivate yourself.")
    if payload.role is not None:
        u.role = payload.role
        u.is_admin = 1 if payload.role == "admin" else 0
    if payload.is_active is not None:
        u.is_active = payload.is_active
    db.commit()
    return {"id": u.id, "role": u.role, "is_active": u.is_active}


# ----------------------------------------------------------------------------- assessments overview
@router.get("/assessments")
def assessments(kind: str = Query("interview", pattern="^(interview|coding)$"), page: int = Query(1, ge=1),
                page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), staff: User = Depends(get_staff_user)):
    if kind == "interview":
        q = db.query(Interview, User.name).join(User, User.id == Interview.user_id).order_by(Interview.started_at.desc())
        return paginate(q, PageParams(page=page, page_size=page_size), lambda r: {
            "id": r[0].id, "student": r[1], "type": r[0].interview_type, "topic": r[0].topic, "adaptive": r[0].adaptive,
            "status": r[0].status, "score": r[0].overall_score, "started_at": r[0].started_at, "simulated": r[0].simulated})
    q = db.query(CodingAssessment, User.name).join(User, User.id == CodingAssessment.user_id).order_by(CodingAssessment.started_at.desc())
    return paginate(q, PageParams(page=page, page_size=page_size), lambda r: {
        "id": r[0].id, "student": r[1], "title": r[0].title, "status": r[0].status, "score": r[0].score,
        "duration_minutes": r[0].duration_seconds // 60, "started_at": r[0].started_at})


# ----------------------------------------------------------------------------- interview question bank
class BankItemIn(BaseModel):
    interview_type: str = Field(pattern="^(hr|technical)$")
    topic: str = Field(min_length=2, max_length=60)
    difficulty: str = Field(pattern="^(easy|medium|hard)$")
    question: str = Field(min_length=10, max_length=2000)
    ideal_answer: str = Field(default="", max_length=4000)
    key_points: List[dict] = []  # [{"label": str, "terms": [str]}]
    is_active: bool = True


def _check_bank(p: BankItemIn):
    if p.interview_type == "technical" and p.topic not in TECH_TOPICS:
        raise HTTPException(status_code=400, detail=f"Technical topic must be one of: {', '.join(TECH_TOPICS)}.")
    for kp in p.key_points:
        if not isinstance(kp.get("label"), str) or not isinstance(kp.get("terms", []), list):
            raise HTTPException(status_code=400, detail='Each key point needs a "label" and a list of "terms".')


@router.get("/interview-bank")
def list_bank(topic: Optional[str] = None, interview_type: Optional[str] = None, difficulty: Optional[str] = None,
              page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), db: Session = Depends(get_db),
              staff: User = Depends(get_staff_user)):
    q = db.query(QuestionBankItem)
    if topic:
        q = q.filter(QuestionBankItem.topic == topic)
    if interview_type:
        q = q.filter(QuestionBankItem.interview_type == interview_type)
    if difficulty:
        q = q.filter(QuestionBankItem.difficulty == difficulty)
    return paginate(q.order_by(QuestionBankItem.topic, QuestionBankItem.id), PageParams(page=page, page_size=page_size), bank_out)


@router.post("/interview-bank", status_code=201)
def create_bank_item(payload: BankItemIn, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    _check_bank(payload)
    row = QuestionBankItem(**{**payload.model_dump(), "key_points": json.dumps(payload.key_points)}, source="admin")
    db.add(row)
    db.commit()
    db.refresh(row)
    return bank_out(row)


@router.put("/interview-bank/{item_id}")
def update_bank_item(item_id: int, payload: BankItemIn, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    _check_bank(payload)
    row = db.query(QuestionBankItem).filter(QuestionBankItem.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Question not found.")
    for k, v in payload.model_dump().items():
        setattr(row, k, json.dumps(v) if k == "key_points" else v)
    db.commit()
    return bank_out(row)


@router.delete("/interview-bank/{item_id}", status_code=204)
def delete_bank_item(item_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    row = db.query(QuestionBankItem).filter(QuestionBankItem.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Question not found.")
    db.delete(row)  # past interviews keep their own copy of the question text, so history is unaffected
    db.commit()


# ----------------------------------------------------------------------------- job descriptions
class JDIn(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    company: str = Field(default="", max_length=255)
    description: str = Field(min_length=20, max_length=20000)
    required_skills: Optional[List[str]] = None  # defaults to skills auto-extracted from the description


def _jd(j: JobDescription) -> dict:
    return {"id": j.id, "title": j.title, "company": j.company, "description": j.description,
            "required_skills": json.loads(j.required_skills or "[]"), "created_at": j.created_at}


@router.get("/job-descriptions")
def list_jds(db: Session = Depends(get_db), staff: User = Depends(get_staff_user)):
    return [_jd(j) for j in db.query(JobDescription).order_by(JobDescription.id.desc())]


@router.post("/job-descriptions", status_code=201)
def create_jd(payload: JDIn, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    skills = payload.required_skills if payload.required_skills is not None else find_skills(payload.description)
    j = JobDescription(title=payload.title, company=payload.company, description=payload.description,
                       required_skills=json.dumps(skills), is_public=True, owner_id=None)
    db.add(j)
    db.commit()
    return _jd(j)


@router.put("/job-descriptions/{jd_id}")
def update_jd(jd_id: int, payload: JDIn, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    j = db.query(JobDescription).filter(JobDescription.id == jd_id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Job description not found.")
    j.title, j.company, j.description = payload.title, payload.company, payload.description
    j.required_skills = json.dumps(payload.required_skills if payload.required_skills is not None else find_skills(payload.description))
    db.commit()
    return _jd(j)


@router.delete("/job-descriptions/{jd_id}", status_code=204)
def delete_jd(jd_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    j = db.query(JobDescription).filter(JobDescription.id == jd_id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Job description not found.")
    from app.models.resume import ResumeJDMatch
    db.query(ResumeJDMatch).filter(ResumeJDMatch.jd_id == jd_id).update({"jd_id": None})
    db.delete(j)
    db.commit()


# ----------------------------------------------------------------------------- analytics + institutional reports
@router.get("/analytics")
def analytics(db: Session = Depends(get_db), staff: User = Depends(get_staff_user)):
    return adm.institution_analytics(db)


@router.get("/reports/institution")
def institution_report(format: str = Query("json", pattern="^(json|csv)$"), branch: Optional[str] = None,
                       graduation_year: Optional[int] = None, db: Session = Depends(get_db), staff: User = Depends(get_staff_user)):
    if format == "csv":
        return Response(adm.institution_csv(db, branch, graduation_year), media_type="text/csv",
                        headers={"Content-Disposition": 'attachment; filename="placement-report.csv"'})
    rows = [adm.student_row(db, u, p) for u, p in adm.student_query(db, None, branch, graduation_year)]
    scores = [r["readiness"] for r in rows]
    return {"students": rows, "count": len(rows), "avg_readiness": round(sum(scores) / len(scores), 1) if scores else None,
            "generated_at": dt.datetime.utcnow()}
