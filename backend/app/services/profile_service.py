"""Profile assembly, resume auto-fill and the placement-readiness score (all computed from stored data)."""
import json
from typing import Any, Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.data.skills import canonical
from app.models.interview import Interview
from app.models.coding import CodingSubmission
from app.models.resume import Resume, Skill, Project
from app.models.user import User, Profile, Certification, Internship
from app.schemas.user import ProfileOut, SkillIn, ProjectIn, CertificationIn, InternshipIn
from app.services import resume_service as rs


def get_or_create_profile(db: Session, user: User) -> Profile:
    p = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not p:
        p = Profile(user_id=user.id)
        db.add(p)
        db.commit()
        db.refresh(p)
    return p


def build_profile_out(db: Session, user: User) -> ProfileOut:
    p = get_or_create_profile(db, user)
    skills = db.query(Skill).filter(Skill.user_id == user.id).order_by(Skill.id).all()
    projects = db.query(Project).filter(Project.user_id == user.id).order_by(Project.id).all()
    certs = db.query(Certification).filter(Certification.user_id == user.id).order_by(Certification.id).all()
    interns = db.query(Internship).filter(Internship.user_id == user.id).order_by(Internship.id).all()
    return ProfileOut(
        college=p.college or "", degree=p.degree or "", target_role=p.target_role or "",
        experience_years=p.experience_years or "0", skills_text=p.skills_text or "", projects_text=p.projects_text or "",
        phone=p.phone or "", location=p.location or "", branch=p.branch or "", graduation_year=p.graduation_year,
        cgpa=p.cgpa, github_url=p.github_url or "", linkedin_url=p.linkedin_url or "", leetcode_url=p.leetcode_url or "",
        portfolio_url=p.portfolio_url or "", career_objective=p.career_objective or "",
        preferred_companies=json.loads(p.preferred_companies or "[]"), target_roles=json.loads(p.target_roles or "[]"),
        has_photo=bool(p.photo_path),
        skills=[SkillIn(name=s.name, proficiency=s.proficiency or "intermediate") for s in skills],
        projects=[ProjectIn(title=x.title, description=x.description or "", technologies=x.technologies or "",
                            github_url=x.github_url or "") for x in projects],
        certifications=[CertificationIn(name=c.name, issuer=c.issuer or "", year=c.year, url=c.url or "") for c in certs],
        internships=[InternshipIn(company=i.company, role=i.role or "", start_date=i.start_date or "",
                                  end_date=i.end_date or "", description=i.description or "") for i in interns],
    )


def apply_profile_update(db: Session, user: User, payload) -> None:
    p = get_or_create_profile(db, user)
    data = payload.model_dump(exclude_unset=True)
    if data.get("name"):
        user.name = data["name"].strip()
    for f in ("college", "degree", "target_role", "experience_years", "phone", "location", "branch", "graduation_year",
              "cgpa", "github_url", "linkedin_url", "leetcode_url", "portfolio_url", "career_objective"):
        if f in data and data[f] is not None:
            setattr(p, f, data[f])
    for f in ("preferred_companies", "target_roles"):
        if data.get(f) is not None:
            setattr(p, f, json.dumps([x.strip() for x in data[f] if x.strip()][:20]))

    if payload.skills is not None:
        db.query(Skill).filter(Skill.user_id == user.id).delete()
        names = []
        for s in payload.skills:
            item = SkillIn(name=s) if isinstance(s, str) else s
            if item.name.strip():
                name = canonical(item.name)
                db.add(Skill(user_id=user.id, name=name, proficiency=item.proficiency))
                names.append(name)
        p.skills_text = ", ".join(names)
    if payload.projects is not None:
        db.query(Project).filter(Project.user_id == user.id).delete()
        titles = []
        for x in payload.projects:
            item = ProjectIn(title=x) if isinstance(x, str) else x
            if item.title.strip():
                db.add(Project(user_id=user.id, title=item.title.strip()[:255], description=item.description,
                               technologies=item.technologies, github_url=item.github_url))
                titles.append(item.title.strip())
        p.projects_text = "; ".join(titles)
    if payload.certifications is not None:
        db.query(Certification).filter(Certification.user_id == user.id).delete()
        for c in payload.certifications:
            db.add(Certification(user_id=user.id, **c.model_dump()))
    if payload.internships is not None:
        db.query(Internship).filter(Internship.user_id == user.id).delete()
        for i in payload.internships:
            db.add(Internship(user_id=user.id, **i.model_dump()))
    db.add(p)
    db.commit()


def autofill_from_resume(db: Session, user: User, resume: Resume, overwrite: bool) -> Dict[str, Any]:
    """Fill the profile from a parsed resume. Existing user-entered values are kept unless overwrite=True."""
    p = get_or_create_profile(db, user)
    analysis = json.loads(resume.analysis or "{}")
    contacts, edu = analysis.get("contacts", {}), analysis.get("education_details", {})
    changed: List[str] = []

    def setf(field, value):
        if value in (None, "", []):
            return
        if overwrite or not getattr(p, field):
            setattr(p, field, value)
            changed.append(field)

    setf("phone", contacts.get("phone"))
    setf("github_url", contacts.get("github"))
    setf("linkedin_url", contacts.get("linkedin"))
    setf("leetcode_url", contacts.get("leetcode"))
    for f in ("college", "degree", "branch", "graduation_year", "cgpa"):
        setf(f, edu.get(f))

    have = {s.name.lower() for s in db.query(Skill).filter(Skill.user_id == user.id)}
    if overwrite:
        db.query(Skill).filter(Skill.user_id == user.id).delete()
        have = set()
    added_skills = []
    for s in rs.all_skills_of(resume):
        if s.lower() not in have:
            db.add(Skill(user_id=user.id, name=s, proficiency="intermediate"))  # proficiency is not inferable; user edits it
            added_skills.append(s)
    if added_skills:
        changed.append("skills")
        p.skills_text = ", ".join(sorted(have | {s.lower() for s in added_skills}))

    existing_titles = {x.title.lower() for x in db.query(Project).filter(Project.user_id == user.id)}
    added_projects = []
    for pr in analysis.get("projects", []):
        title = pr["title"][:255]
        if title and title.lower() not in existing_titles:
            db.add(Project(user_id=user.id, title=title, description=" ".join(pr.get("details", []))[:2000],
                           technologies=", ".join(rs.find_skills(" ".join(pr.get("details", []) + [title])))[:500]))
            added_projects.append(title)
    if added_projects:
        changed.append("projects")

    existing_certs = {c.name.lower() for c in db.query(Certification).filter(Certification.user_id == user.id)}
    added_certs = [c for c in json.loads(resume.extracted_certifications or "[]") if c.lower() not in existing_certs]
    for c in added_certs:
        db.add(Certification(user_id=user.id, name=c[:255]))
    if added_certs:
        changed.append("certifications")
    db.commit()
    return {"updated_fields": changed, "added_skills": added_skills, "added_projects": added_projects,
            "added_certifications": added_certs}


def readiness(db: Session, user: User) -> Dict[str, Any]:
    """Placement readiness 0-100 from real data. Components without data are excluded and weights renormalised."""
    prof = build_profile_out(db, user)
    checks = {
        "basic details": bool(prof.college and prof.degree and prof.branch and prof.graduation_year),
        "cgpa": prof.cgpa is not None,
        "skills (5+)": len(prof.skills) >= 5,
        "projects (2+)": len(prof.projects) >= 2,
        "internship or certification": bool(prof.internships or prof.certifications),
        "profile links": bool(prof.github_url or prof.linkedin_url or prof.leetcode_url),
        "career objective": bool(prof.career_objective),
        "target roles/companies": bool(prof.target_roles or prof.preferred_companies),
    }
    completeness = 100 * sum(checks.values()) / len(checks)
    resume = db.query(Resume).filter(Resume.user_id == user.id, Resume.is_active == True).first()  # noqa: E712
    comps: Dict[str, Dict[str, Any]] = {"profile_completeness": {"score": round(completeness, 1), "weight": 0.2}}
    if resume and resume.quality_score is not None:
        comps["resume"] = {"score": round(0.5 * resume.quality_score + 0.5 * (resume.ats_score or 0), 1), "weight": 0.2}
    iv = db.query(func.avg(Interview.overall_score), func.count(Interview.id)).filter(
        Interview.user_id == user.id, Interview.status == "completed", Interview.overall_score.isnot(None)).one()
    if iv[1]:
        comps["interviews"] = {"score": round(float(iv[0]), 1), "weight": 0.35}
    cd = db.query(func.avg(CodingSubmission.score), func.count(CodingSubmission.id)).filter(
        CodingSubmission.user_id == user.id, CodingSubmission.status != "pending").one()
    if cd[1]:
        comps["coding"] = {"score": round(float(cd[0]), 1), "weight": 0.25}
    total_w = sum(c["weight"] for c in comps.values())
    score = sum(c["score"] * c["weight"] for c in comps.values()) / total_w
    missing = [k for k, v in checks.items() if not v]
    band = "Interview ready" if score >= 75 else "Getting there" if score >= 55 else "Needs preparation"
    return {"score": round(score, 1), "band": band, "components": comps, "profile_gaps": missing,
            "not_yet_measured": [c for c in ("resume", "interviews", "coding") if c not in comps]}
