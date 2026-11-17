"""Skill gap, roadmap, analytics and company-prep endpoints (all data-driven)."""
import datetime as dt
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.data.companies import COMPANIES
from app.data.roles import TOPIC_STUDY_NOTES
from app.database import get_db
from app.models.roadmap import Roadmap, RoadmapTask
from app.models.user import User
from app.services import analytics_service as an
from app.services import roadmap_service as rms
from app.services import skill_gap_service as sg
from app.services import adaptive_engine as eng
from app.utils.security import get_current_user

router = APIRouter(tags=["Insights"])


# ------------------------------------------------------------------ skill gap
@router.get("/skill-gap/roles")
def roles(current_user: User = Depends(get_current_user)):
    return {"roles": sg.available_roles()}


@router.get("/skill-gap")
def skill_gap(role: Optional[str] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return sg.analyze(db, current_user.id, role)


# ------------------------------------------------------------------ analytics
@router.get("/analytics/me")
def my_analytics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return an.student_analytics(db, current_user.id)


# ------------------------------------------------------------------ roadmap
class RoadmapCreate(BaseModel):
    weeks: int = Field(default=4, ge=1, le=12)
    hours_per_day: float = Field(default=2, ge=0.5, le=8)
    role: Optional[str] = Field(default=None, max_length=100)


def _task(t: RoadmapTask) -> dict:
    return {"id": t.id, "due_date": t.due_date.isoformat(), "week_index": t.week_index, "topic": t.topic, "title": t.title,
            "description": t.description, "task_type": t.task_type, "est_minutes": t.est_minutes, "status": t.status,
            "completed_at": t.completed_at}


def _roadmap_out(rm: Roadmap) -> dict:
    tasks = sorted(rm.tasks, key=lambda t: (t.due_date, t.task_type))
    today = dt.date.today()
    return {"id": rm.id, "title": rm.title, "target_role": rm.target_role, "weeks": rm.weeks, "hours_per_day": rm.hours_per_day,
            "start_date": rm.start_date.isoformat(), "status": rm.status, "progress": rms.progress(rm),
            "weekly_targets": json.loads(rm.weekly_targets or "[]"), "basis": json.loads(rm.basis or "{}"),
            "today": [_task(t) for t in tasks if t.due_date == today],
            "tasks": [_task(t) for t in tasks]}


def _active(db, user) -> Roadmap:
    rm = db.query(Roadmap).filter(Roadmap.user_id == user.id, Roadmap.status == "active").order_by(Roadmap.id.desc()).first()
    if not rm:
        raise HTTPException(status_code=404, detail="No active roadmap. Generate one first.")
    return rm


@router.post("/roadmap", status_code=201)
def create_roadmap(payload: RoadmapCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rm = rms.generate(db, current_user.id, payload.weeks, payload.hours_per_day, payload.role)
    return _roadmap_out(rm)


@router.get("/roadmap")
def get_roadmap(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _roadmap_out(_active(db, current_user))


@router.post("/roadmap/refresh")
def refresh_roadmap(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rm = _active(db, current_user)
    change = rms.refresh(db, rm)
    db.refresh(rm)
    return {"changes": change, "roadmap": _roadmap_out(rm)}


class TaskUpdate(BaseModel):
    status: str = Field(pattern="^(todo|done)$")


@router.patch("/roadmap/tasks/{task_id}")
def update_task(task_id: int, payload: TaskUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = (db.query(RoadmapTask).join(Roadmap, Roadmap.id == RoadmapTask.roadmap_id)
         .filter(RoadmapTask.id == task_id, Roadmap.user_id == current_user.id).first())
    if not t:
        raise HTTPException(status_code=404, detail="Task not found.")
    t.status = payload.status
    t.completed_at = dt.datetime.utcnow() if payload.status == "done" else None
    db.commit()
    return {"task": _task(t), "progress": rms.progress(t.roadmap)}


# ------------------------------------------------------------------ company prep
@router.get("/companies")
def list_companies(current_user: User = Depends(get_current_user)):
    return [{"slug": k, "name": v["name"], "category": v["category"]} for k, v in COMPANIES.items()]


@router.get("/companies/{slug}")
def company_guide(slug: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = COMPANIES.get(slug.lower())
    if not c:
        raise HTTPException(status_code=404, detail="Unknown company.")
    interview = eng.topic_history(db, current_user.id)
    coding = sg.coding_topic_scores(db, current_user.id)
    focus = []
    for t in c["focus_topics"]:
        parts = [x["avg"] for x in (interview.get(t), coding.get(t)) if x]
        focus.append({"topic": t, "notes": TOPIC_STUDY_NOTES.get(t, ""), "your_score": round(sum(parts) / len(parts), 1) if parts else None,
                      "status": "not_attempted" if not parts else ("strong" if sum(parts) / len(parts) >= 75 else "needs_work")})
    measured = [f["your_score"] for f in focus if f["your_score"] is not None]
    return {**c, "slug": slug.lower(), "focus": focus,
            "readiness": round(sum(measured) / len(measured), 1) if measured else None,
            "readiness_basis": f"{len(measured)} of {len(focus)} focus topics attempted" ,
            "weakest": [f["topic"] for f in sorted([f for f in focus if f["your_score"] is not None], key=lambda f: f["your_score"])[:2]],
            "not_attempted": [f["topic"] for f in focus if f["your_score"] is None]}


# ------------------------------------------------------------------ voice analysis
class SpeechAnalyzeRequest(BaseModel):
    transcript: str = Field(min_length=1, max_length=20000)
    duration_seconds: Optional[float] = Field(default=None, ge=0, le=3600)
    pauses: Optional[list[float]] = None


@router.post("/speech/analyze")
def analyze_speech_endpoint(payload: SpeechAnalyzeRequest, current_user: User = Depends(get_current_user)):
    """WPM, filler words, pauses and delivery feedback from a transcript + timings measured in the browser."""
    from app.services.speech_analysis import analyze_speech
    return analyze_speech(payload.transcript, payload.duration_seconds, payload.pauses)


@router.get("/speech/capabilities")
def speech_capabilities(current_user: User = Depends(get_current_user)):
    return {"stt": "browser Web Speech API (Chrome/Edge; audio is processed by the browser vendor's service)",
            "tts": "browser speechSynthesis (read questions aloud)",
            "server_side_audio": False,
            "note": "No audio is uploaded to this server; only the transcript and timings are sent."}
