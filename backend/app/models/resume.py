import datetime as dt
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Float
from sqlalchemy.orm import relationship

from app.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    original_filename = Column(String(500))
    file_path = Column(String(1000))
    raw_text = Column(Text, default="")
    extracted_skills = Column(Text, default="")       # JSON-encoded list
    extracted_technologies = Column(Text, default="")  # JSON-encoded list
    extracted_projects = Column(Text, default="")      # JSON-encoded list
    extracted_education = Column(Text, default="")     # JSON-encoded list
    extracted_experience = Column(Text, default="")    # JSON-encoded list
    extracted_certifications = Column(Text, default="")  # JSON-encoded list
    keywords = Column(Text, default="")                 # JSON-encoded list
    uploaded_at = Column(DateTime, default=dt.datetime.utcnow)

    # ---- versioning + intelligence ----
    version = Column(Integer, default=1, server_default="1", nullable=False)
    label = Column(String(120), default="")
    is_active = Column(Boolean, default=True, server_default="true", nullable=False)
    ats_score = Column(Float, nullable=True)
    quality_score = Column(Float, nullable=True)
    analysis = Column(Text, default="")  # JSON: ATS checks, quality breakdown, suggestions, contact links

    user = relationship("User", back_populates="resumes")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100), default="general")
    proficiency = Column(String(50), default="intermediate")  # beginner|intermediate|advanced|expert


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    technologies = Column(String(500), default="")
    github_url = Column(String(500), default="")


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), default="")
    description = Column(Text, nullable=False)
    required_skills = Column(Text, default="[]")  # JSON list (auto-extracted, editable)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # null -> admin-managed, visible to all
    is_public = Column(Boolean, default=True, server_default="true", nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)


class ResumeJDMatch(Base):
    __tablename__ = "resume_jd_matches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    jd_id = Column(Integer, ForeignKey("job_descriptions.id"), nullable=True)
    jd_title = Column(String(255), default="")
    match_score = Column(Float, default=0)
    matched_skills = Column(Text, default="[]")
    missing_skills = Column(Text, default="[]")
    suggestions = Column(Text, default="[]")
    created_at = Column(DateTime, default=dt.datetime.utcnow)
