from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class ResumeOut(BaseModel):
    id: int
    original_filename: str
    extracted_skills: List[str]
    extracted_technologies: List[str]
    extracted_projects: List[str]
    extracted_education: List[str]
    extracted_experience: List[str]
    extracted_certifications: List[str]
    keywords: List[str]
    uploaded_at: datetime
    version: int = 1
    label: str = ""
    is_active: bool = True
    ats_score: Optional[float] = None
    quality_score: Optional[float] = None
    analysis: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class ResumeSummary(BaseModel):
    id: int
    original_filename: str
    version: int
    label: str = ""
    is_active: bool
    ats_score: Optional[float] = None
    quality_score: Optional[float] = None
    uploaded_at: datetime


class JDMatchRequest(BaseModel):
    resume_id: Optional[int] = None
    jd_id: Optional[int] = None
    jd_text: Optional[str] = Field(default=None, max_length=20000)
    jd_title: Optional[str] = Field(default="", max_length=255)


class JDMatchOut(BaseModel):
    id: int
    resume_id: int
    jd_title: str
    match_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    suggestions: List[str]
    created_at: datetime


class JDCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    company: str = Field(default="", max_length=255)
    description: str = Field(min_length=20, max_length=20000)
    is_public: bool = True


class JDOut(BaseModel):
    id: int
    title: str
    company: str
    description: str
    required_skills: List[str]
    is_public: bool
