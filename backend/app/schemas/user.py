from typing import Optional, List, Union
from pydantic import BaseModel, Field


class SkillIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    proficiency: str = Field(default="intermediate", pattern="^(beginner|intermediate|advanced|expert)$")


class ProjectIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    technologies: str = Field(default="", max_length=500)
    github_url: str = Field(default="", max_length=500)


class CertificationIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    issuer: str = Field(default="", max_length=255)
    year: Optional[int] = Field(default=None, ge=1990, le=2100)
    url: str = Field(default="", max_length=500)


class InternshipIn(BaseModel):
    company: str = Field(min_length=1, max_length=255)
    role: str = Field(default="", max_length=255)
    start_date: str = Field(default="", max_length=20)
    end_date: str = Field(default="", max_length=20)
    description: str = Field(default="", max_length=2000)


class ProfileOut(BaseModel):
    college: str = ""
    degree: str = ""
    target_role: str = "Software Developer"
    experience_years: str = "0"
    skills_text: str = ""
    projects_text: str = ""
    phone: str = ""
    location: str = ""
    branch: str = ""
    graduation_year: Optional[int] = None
    cgpa: Optional[float] = None
    github_url: str = ""
    linkedin_url: str = ""
    leetcode_url: str = ""
    portfolio_url: str = ""
    career_objective: str = ""
    preferred_companies: List[str] = []
    target_roles: List[str] = []
    has_photo: bool = False
    skills: List[SkillIn] = []
    projects: List[ProjectIn] = []
    certifications: List[CertificationIn] = []
    internships: List[InternshipIn] = []


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    college: Optional[str] = Field(default=None, max_length=255)
    degree: Optional[str] = Field(default=None, max_length=255)
    target_role: Optional[str] = Field(default=None, max_length=255)
    experience_years: Optional[str] = Field(default=None, max_length=50)
    phone: Optional[str] = Field(default=None, max_length=40)
    location: Optional[str] = Field(default=None, max_length=255)
    branch: Optional[str] = Field(default=None, max_length=255)
    graduation_year: Optional[int] = Field(default=None, ge=1990, le=2100)
    cgpa: Optional[float] = Field(default=None, ge=0, le=10)
    github_url: Optional[str] = Field(default=None, max_length=500)
    linkedin_url: Optional[str] = Field(default=None, max_length=500)
    leetcode_url: Optional[str] = Field(default=None, max_length=500)
    portfolio_url: Optional[str] = Field(default=None, max_length=500)
    career_objective: Optional[str] = Field(default=None, max_length=2000)
    preferred_companies: Optional[List[str]] = None
    target_roles: Optional[List[str]] = None
    skills: Optional[List[Union[SkillIn, str]]] = None
    projects: Optional[List[Union[ProjectIn, str]]] = None
    certifications: Optional[List[CertificationIn]] = None
    internships: Optional[List[InternshipIn]] = None


class MeResponse(BaseModel):
    id: int
    name: str
    email: str
    is_admin: bool = False
    role: str = "student"
    profile: ProfileOut

    class Config:
        from_attributes = True


class AutofillRequest(BaseModel):
    resume_id: Optional[int] = None
    overwrite: bool = False
