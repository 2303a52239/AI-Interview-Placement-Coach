"""
CandidateContextRetriever

Ties together candidate data (resume text, skills, projects, target role,
previous interview results) into a single retrieval step that feeds the
AIProvider when generating personalized questions - this is the RAG piece
of the pipeline described in the project spec.
"""
import json
from typing import List

from sqlalchemy.orm import Session

from app.models.resume import Resume, Skill, Project
from app.models.user import Profile
from app.models.interview import Interview, InterviewQuestion, InterviewAnswer, Evaluation
from app.rag.vector_store import SimpleVectorStore


class CandidateContextRetriever:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.store = SimpleVectorStore()

    def _collect_source_documents(self) -> List[str]:
        docs: List[str] = []

        profile = self.db.query(Profile).filter(Profile.user_id == self.user_id).first()
        if profile:
            docs.append(f"Target role: {profile.target_role}. Experience: {profile.experience_years} years.")
            if profile.skills_text:
                docs.append(f"Skills: {profile.skills_text}")
            if profile.projects_text:
                docs.append(f"Projects: {profile.projects_text}")

        skills = self.db.query(Skill).filter(Skill.user_id == self.user_id).all()
        if skills:
            docs.append("Skill list: " + ", ".join(s.name for s in skills))

        projects = self.db.query(Project).filter(Project.user_id == self.user_id).all()
        for p in projects:
            docs.append(f"Project '{p.title}' using {p.technologies}: {p.description}")

        resume = (
            self.db.query(Resume)
            .filter(Resume.user_id == self.user_id)
            .order_by(Resume.uploaded_at.desc())
            .first()
        )
        if resume and resume.raw_text:
            docs.extend(self.store.build_from_text(resume.raw_text))

        # previous interview weaknesses / recommended topics -> personalize further
        past_interviews = (
            self.db.query(Interview)
            .filter(Interview.user_id == self.user_id, Interview.status == "completed")
            .order_by(Interview.completed_at.desc())
            .limit(3)
            .all()
        )
        for interview in past_interviews:
            try:
                weaknesses = json.loads(interview.weaknesses or "[]")
                topics = json.loads(interview.recommended_topics or "[]")
            except json.JSONDecodeError:
                weaknesses, topics = [], []
            if weaknesses:
                docs.append("Previous weak areas: " + ", ".join(weaknesses))
            if topics:
                docs.append("Previously recommended topics: " + ", ".join(topics))

        return docs

    def get_context(self, query: str, top_k: int = 8) -> str:
        docs = self._collect_source_documents()
        if not docs:
            return ""
        return self.store.retrieve(query, docs, top_k=top_k)
