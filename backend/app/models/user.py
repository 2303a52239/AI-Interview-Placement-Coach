import datetime as dt
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Float
from sqlalchemy.orm import relationship

from app.database import Base

ROLE_STUDENT = "student"
ROLE_ADMIN = "admin"
ROLE_OFFICER = "placement_officer"  # read-only access to institutional reports


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    is_admin = Column(Integer, default=0)  # kept for backward compatibility; role is authoritative
    role = Column(String(30), default=ROLE_STUDENT, server_default=ROLE_STUDENT, nullable=False)
    is_active = Column(Boolean, default=True, server_default="true", nullable=False)
    last_login_at = Column(DateTime, nullable=True)

    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="user", cascade="all, delete-orphan")
    coding_submissions = relationship("CodingSubmission", back_populates="user", cascade="all, delete-orphan")
    performance_snapshots = relationship("PerformanceSnapshot", back_populates="user", cascade="all, delete-orphan")
    preparation_plans = relationship("PreparationPlan", back_populates="user", cascade="all, delete-orphan")

    @property
    def is_admin_role(self) -> bool:
        return self.role == ROLE_ADMIN or bool(self.is_admin)


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    college = Column(String(255), default="")  # university / institution
    degree = Column(String(255), default="")
    target_role = Column(String(255), default="Software Developer")
    experience_years = Column(String(50), default="0")
    skills_text = Column(Text, default="")
    projects_text = Column(Text, default="")
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    # ---- advanced profile ----
    phone = Column(String(40), default="")
    location = Column(String(255), default="")
    branch = Column(String(255), default="")
    graduation_year = Column(Integer, nullable=True)
    cgpa = Column(Float, nullable=True)
    github_url = Column(String(500), default="")
    linkedin_url = Column(String(500), default="")
    leetcode_url = Column(String(500), default="")
    portfolio_url = Column(String(500), default="")
    career_objective = Column(Text, default="")
    preferred_companies = Column(Text, default="[]")  # JSON list
    target_roles = Column(Text, default="[]")  # JSON list
    photo_path = Column(String(1000), default="")

    user = relationship("User", back_populates="profile")


class Certification(Base):
    __tablename__ = "certifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    issuer = Column(String(255), default="")
    year = Column(Integer, nullable=True)
    url = Column(String(500), default="")


class Internship(Base):
    __tablename__ = "internships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    company = Column(String(255), nullable=False)
    role = Column(String(255), default="")
    start_date = Column(String(20), default="")
    end_date = Column(String(20), default="")
    description = Column(Text, default="")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    jti = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, server_default="false", nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
