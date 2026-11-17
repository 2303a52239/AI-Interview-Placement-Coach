import json
import datetime as dt
import random
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.ai import usage
from app.ai.factory import get_ai_provider
from app.coding import complexity
from app.coding.executor import run_submission, RunResult
from app.config import settings
from app.models.coding import CodingQuestion, CodingSubmission, CodingAssessment
from app.models.performance import PerformanceSnapshot

DEFAULT_STARTERS = {
    "python": "# Read from standard input and print the answer.\n\ndef main():\n    pass\n\n\nif __name__ == \"__main__\":\n    main()\n",
    "java": "import java.util.*;\n\npublic class Solution {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        \n    }\n}\n",
    "cpp": "#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n    \n    return 0;\n}\n",
}


def parse_tests(question: CodingQuestion) -> List[dict]:
    return json.loads(question.test_cases or "[]")


def question_out(q: CodingQuestion) -> dict:
    tests = parse_tests(q)
    starters = {**DEFAULT_STARTERS, **json.loads(q.starter_codes or "{}")}
    if q.starter_code:
        starters["java"] = q.starter_code if "starter_codes" not in (q.starter_codes or "") else starters["java"]
    hidden = sum(1 for t in tests if t.get("hidden"))
    return {"id": q.id, "title": q.title, "problem_statement": q.problem_statement, "input_format": q.input_format,
            "output_format": q.output_format, "constraints": q.constraints, "sample_input": q.sample_input,
            "sample_output": q.sample_output, "difficulty": q.difficulty, "topic_tag": q.topic_tag,
            "starter_code": q.starter_code or starters["java"], "starter_codes": starters,
            "time_limit_seconds": q.time_limit_seconds or settings.EXEC_TIMEOUT_SECONDS,
            "company_tags": json.loads(q.company_tags or "[]"),
            "visible_tests": len(tests) - hidden, "hidden_tests": hidden}


def _present_cases(run: RunResult) -> List[dict]:
    out = []
    for c in run.cases:
        if c.hidden:  # hidden test data is never sent to the client
            out.append({"passed": c.passed, "hidden": True, "status": c.status, "time_ms": c.time_ms})
        else:
            out.append({"input": c.input, "expected_output": c.expected_output, "actual_output": c.actual_output,
                        "passed": c.passed, "hidden": False, "status": c.status, "time_ms": c.time_ms})
    return out


def run_sample(question: CodingQuestion, source: str, language: str) -> RunResult:
    sample = [{"input": question.sample_input, "expected_output": question.sample_output}]
    return run_submission(language, source, sample, question.time_limit_seconds or None)


def _active_assessment(db: Session, user_id: int, assessment_id: int, question_id: int) -> CodingAssessment:
    from fastapi import HTTPException
    a = db.query(CodingAssessment).filter(CodingAssessment.id == assessment_id, CodingAssessment.user_id == user_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found.")
    if question_id not in json.loads(a.question_ids):
        raise HTTPException(status_code=400, detail="This question is not part of the assessment.")
    refresh_assessment_status(db, a)
    if a.status != "in_progress":
        raise HTTPException(status_code=400, detail="This assessment has ended; submissions are closed.")
    return a


def submit_code(db: Session, user_id: int, question: CodingQuestion, source_code: str, language: str = "java",
                assessment_id: Optional[int] = None) -> Tuple[CodingSubmission, List[dict], dict]:
    if assessment_id:
        _active_assessment(db, user_id, assessment_id, question.id)
    tests = parse_tests(question)
    run = run_submission(language, source_code, tests, question.time_limit_seconds or None)
    compile_ok = run.status not in ("compiled_error", "timeout", "sandbox_error")
    total = len(tests)
    passed = run.passed_count
    hidden_total = sum(1 for t in tests if t.get("hidden"))
    hidden_passed = sum(1 for c in run.cases if c.hidden and c.passed)

    provider = get_ai_provider()
    ai = provider.evaluate_code(question.problem_statement, source_code, passed, max(total, 1), compile_ok)
    est = complexity.analyze(language, source_code)
    if provider.simulated or not ai.get("time_complexity_estimate"):
        ai = {**ai, "time_complexity_estimate": est["time"] if compile_ok else "N/A",
              "space_complexity_estimate": est["space"] if compile_ok else "N/A"}
    score = round(passed / total * 100, 1) if total else 0.0

    sub = CodingSubmission(
        user_id=user_id, question_id=question.id, source_code=source_code, status=run.status,
        compile_output=run.compile_output, passed_test_cases=passed, total_test_cases=total,
        execution_time_ms=run.execution_time_ms, time_complexity_estimate=ai.get("time_complexity_estimate", ""),
        space_complexity_estimate=ai.get("space_complexity_estimate", ""), score=score,
        ai_feedback=ai.get("feedback", ""), submitted_at=dt.datetime.utcnow(), language=language,
        assessment_id=assessment_id, hidden_passed=hidden_passed, hidden_total=hidden_total, sandbox=run.sandbox)
    db.add(sub)
    db.flush()
    if run.status != "sandbox_error":  # an infrastructure failure must not count against the student
        db.add(PerformanceSnapshot(user_id=user_id, source_type="coding", source_id=sub.id, score=score,
                                   difficulty=question.difficulty, skill_tags=json.dumps([question.topic_tag])))
    usage.persist(db, user_id)
    db.commit()
    db.refresh(sub)
    return sub, _present_cases(run), est


# ------------------------------------------------------------------ timed assessments
def start_assessment(db: Session, user_id: int, num_questions: int, duration_minutes: int,
                     difficulty: Optional[str], company: Optional[str]) -> CodingAssessment:
    from fastapi import HTTPException
    q = db.query(CodingQuestion)
    if difficulty:
        q = q.filter(CodingQuestion.difficulty == difficulty)
    pool = q.all()
    if company:
        from app.data.companies import COMPANIES
        guide_tags = set(COMPANIES.get(company.lower(), {}).get("coding_tags", []))
        pool = [x for x in pool if x.topic_tag in guide_tags or company.lower() in [c.lower() for c in json.loads(x.company_tags or "[]")]]
    if not pool:
        raise HTTPException(status_code=404, detail="No coding questions match those filters.")
    solved = {sid for (sid,) in db.query(CodingSubmission.question_id).filter(
        CodingSubmission.user_id == user_id, CodingSubmission.score >= 100).all()}
    pool.sort(key=lambda x: (x.id in solved, random.random()))  # unsolved first
    chosen = pool[:num_questions]
    now = dt.datetime.utcnow()
    a = CodingAssessment(user_id=user_id, title=f"{company.title() + ' ' if company else ''}Timed coding interview",
                         question_ids=json.dumps([c.id for c in chosen]), duration_seconds=duration_minutes * 60,
                         started_at=now, deadline=now + dt.timedelta(minutes=duration_minutes), company_slug=company or "")
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def assessment_scores(db: Session, a: CodingAssessment) -> Dict[int, float]:
    best: Dict[int, float] = {}
    for s in db.query(CodingSubmission).filter(CodingSubmission.assessment_id == a.id).all():
        best[s.question_id] = max(best.get(s.question_id, 0.0), s.score or 0.0)
    return best


def finalize(db: Session, a: CodingAssessment, status: str) -> None:
    ids = json.loads(a.question_ids)
    best = assessment_scores(db, a)
    a.score = round(sum(best.get(i, 0.0) for i in ids) / len(ids), 1) if ids else 0.0
    a.status = status
    a.finished_at = min(dt.datetime.utcnow(), a.deadline) if status == "expired" else dt.datetime.utcnow()
    db.commit()


def refresh_assessment_status(db: Session, a: CodingAssessment) -> CodingAssessment:
    if a.status == "in_progress" and dt.datetime.utcnow() >= a.deadline:
        finalize(db, a, "expired")
    return a


def assessment_out(db: Session, a: CodingAssessment) -> dict:
    refresh_assessment_status(db, a)
    ids = json.loads(a.question_ids)
    qs = {q.id: q for q in db.query(CodingQuestion).filter(CodingQuestion.id.in_(ids)).all()}
    remaining = max(0, int((a.deadline - dt.datetime.utcnow()).total_seconds())) if a.status == "in_progress" else 0
    return {"id": a.id, "title": a.title, "status": a.status, "duration_seconds": a.duration_seconds,
            "remaining_seconds": remaining, "started_at": a.started_at, "deadline": a.deadline, "score": a.score,
            "questions": [question_out(qs[i]) for i in ids if i in qs], "best_scores": assessment_scores(db, a)}
