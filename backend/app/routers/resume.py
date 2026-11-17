import json
import os
from typing import List

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.resume import Resume, JobDescription, ResumeJDMatch
from app.schemas.resume import ResumeOut, ResumeSummary, JDMatchRequest, JDMatchOut, JDOut
from app.utils.security import get_current_user
from app.utils.file_utils import validate_and_save_upload
from app.services import resume_service as rs

router = APIRouter(prefix="/resume", tags=["Resume"])


def _out(r: Resume) -> ResumeOut:
    return ResumeOut(
        id=r.id, original_filename=r.original_filename,
        extracted_skills=json.loads(r.extracted_skills or "[]"),
        extracted_technologies=json.loads(r.extracted_technologies or "[]"),
        extracted_projects=json.loads(r.extracted_projects or "[]"),
        extracted_education=json.loads(r.extracted_education or "[]"),
        extracted_experience=json.loads(r.extracted_experience or "[]"),
        extracted_certifications=json.loads(r.extracted_certifications or "[]"),
        keywords=json.loads(r.keywords or "[]"), uploaded_at=r.uploaded_at,
        version=r.version, label=r.label or "", is_active=r.is_active,
        ats_score=r.ats_score, quality_score=r.quality_score,
        analysis=json.loads(r.analysis or "{}"),
    )


def _owned(db: Session, user: User, resume_id: int) -> Resume:
    r = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user.id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return r


def _active(db: Session, user: User) -> Resume:
    r = (db.query(Resume).filter(Resume.user_id == user.id, Resume.is_active == True)  # noqa: E712
         .order_by(Resume.version.desc()).first())
    if not r:
        raise HTTPException(status_code=404, detail="No resume uploaded yet.")
    return r


@router.post("/upload", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
def upload_resume(label: str = Query(default="", max_length=120), file: UploadFile = File(...),
                  current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    path = validate_and_save_upload(file, subdir="resumes")
    try:
        raw_text = rs.extract_text(path)
    except Exception as exc:  # noqa: BLE001
        os.remove(path)
        raise HTTPException(status_code=400, detail=f"Could not read the resume file: {exc}") from exc
    if not raw_text.strip():
        os.remove(path)
        raise HTTPException(status_code=400, detail="No readable text was found in this resume (it may be a scanned "
                                                    "image). Please upload a text-based PDF or DOCX.")
    last = db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.version.desc()).first()
    db.query(Resume).filter(Resume.user_id == current_user.id).update({"is_active": False})
    resume = Resume(user_id=current_user.id, original_filename=file.filename, file_path=path, raw_text=raw_text,
                    version=(last.version + 1) if last else 1, label=label, is_active=True,
                    **rs.analyze_resume(raw_text))
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return _out(resume)


@router.get("", response_model=ResumeOut)
def get_active_resume(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _out(_active(db, current_user))


@router.get("/versions", response_model=List[ResumeSummary])
def list_versions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.version.desc()).all()
    return [ResumeSummary(id=r.id, original_filename=r.original_filename, version=r.version, label=r.label or "",
                          is_active=r.is_active, ats_score=r.ats_score, quality_score=r.quality_score,
                          uploaded_at=r.uploaded_at) for r in rows]


@router.get("/job-descriptions", response_model=List[JDOut])
def list_jds(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(JobDescription)
            .filter((JobDescription.is_public == True) | (JobDescription.owner_id == current_user.id))  # noqa: E712
            .order_by(JobDescription.created_at.desc()).all())
    return [JDOut(id=j.id, title=j.title, company=j.company, description=j.description,
                  required_skills=json.loads(j.required_skills or "[]"), is_public=j.is_public) for j in rows]


@router.get("/matches", response_model=List[JDMatchOut])
def list_matches(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(ResumeJDMatch).filter(ResumeJDMatch.user_id == current_user.id)
            .order_by(ResumeJDMatch.created_at.desc()).limit(30).all())
    return [_match_out(m) for m in rows]


def _match_out(m: ResumeJDMatch) -> JDMatchOut:
    return JDMatchOut(id=m.id, resume_id=m.resume_id, jd_title=m.jd_title, match_score=m.match_score,
                      matched_skills=json.loads(m.matched_skills), missing_skills=json.loads(m.missing_skills),
                      suggestions=json.loads(m.suggestions), created_at=m.created_at)


@router.post("/match", response_model=JDMatchOut)
def match_jd(payload: JDMatchRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume = _owned(db, current_user, payload.resume_id) if payload.resume_id else _active(db, current_user)
    jd_skills, title, jd_text = None, payload.jd_title or "Pasted job description", payload.jd_text
    if payload.jd_id:
        jd = db.query(JobDescription).filter(JobDescription.id == payload.jd_id).first()
        if not jd or not (jd.is_public or jd.owner_id == current_user.id):
            raise HTTPException(status_code=404, detail="Job description not found.")
        jd_text, title = jd.description, f"{jd.title} - {jd.company}".strip(" -")
        jd_skills = json.loads(jd.required_skills or "[]") or None
    if not jd_text or len(jd_text.strip()) < 20:
        raise HTTPException(status_code=400, detail="Provide a job description (jd_id or jd_text of at least 20 characters).")
    res = rs.match_resume_to_jd(resume.raw_text, rs.all_skills_of(resume), jd_text, jd_skills)
    m = ResumeJDMatch(user_id=current_user.id, resume_id=resume.id, jd_id=payload.jd_id, jd_title=title,
                      match_score=res["match_score"], matched_skills=json.dumps(res["matched_skills"]),
                      missing_skills=json.dumps(res["missing_skills"]), suggestions=json.dumps(res["suggestions"]))
    db.add(m)
    db.commit()
    db.refresh(m)
    return _match_out(m)


@router.get("/{resume_id}", response_model=ResumeOut)
def get_resume(resume_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _out(_owned(db, current_user, resume_id))


@router.post("/{resume_id}/activate", response_model=ResumeOut)
def activate(resume_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = _owned(db, current_user, resume_id)
    db.query(Resume).filter(Resume.user_id == current_user.id).update({"is_active": False})
    r.is_active = True
    db.commit()
    return _out(r)


@router.delete("/{resume_id}", status_code=204)
def delete_resume(resume_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = _owned(db, current_user, resume_id)
    path, was_active = r.file_path, r.is_active
    db.query(ResumeJDMatch).filter(ResumeJDMatch.resume_id == r.id).delete()
    db.delete(r)
    db.commit()
    if path and os.path.exists(path):
        os.remove(path)
    if was_active:
        nxt = db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.version.desc()).first()
        if nxt:
            nxt.is_active = True
            db.commit()
