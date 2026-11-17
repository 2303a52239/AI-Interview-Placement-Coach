import datetime as dt
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship

from app.database import Base


class CodingQuestion(Base):
    __tablename__ = "coding_questions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    problem_statement = Column(Text, nullable=False)
    input_format = Column(Text, default="")
    output_format = Column(Text, default="")
    constraints = Column(Text, default="")
    sample_input = Column(Text, default="")
    sample_output = Column(Text, default="")
    difficulty = Column(String(20), default="easy")
    topic_tag = Column(String(100), default="general")
    starter_code = Column(Text, default="")  # Java starter (original column, kept)
    # JSON list of {"input": "...", "expected_output": "...", "hidden": bool}
    test_cases = Column(Text, nullable=False)

    # ---- multi-language ----
    starter_codes = Column(Text, default="{}")  # JSON {"python": "...", "java": "...", "cpp": "..."}
    time_limit_seconds = Column(Integer, default=0, server_default="0", nullable=False)  # 0 -> default
    company_tags = Column(Text, default="[]")  # JSON list of company slugs

    submissions = relationship("CodingSubmission", back_populates="question", cascade="all, delete-orphan")


class CodingSubmission(Base):
    __tablename__ = "coding_submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("coding_questions.id"), nullable=False)
    source_code = Column(Text, nullable=False)
    status = Column(String(30), default="pending")
    compile_output = Column(Text, default="")
    passed_test_cases = Column(Integer, default=0)
    total_test_cases = Column(Integer, default=0)
    execution_time_ms = Column(Float, default=0)
    time_complexity_estimate = Column(Text, default="")
    space_complexity_estimate = Column(Text, default="")
    score = Column(Float, default=0)
    ai_feedback = Column(Text, default="")
    submitted_at = Column(DateTime, default=dt.datetime.utcnow)

    language = Column(String(20), default="java", server_default="java", nullable=False)
    assessment_id = Column(Integer, ForeignKey("coding_assessments.id"), nullable=True)
    hidden_passed = Column(Integer, default=0, server_default="0", nullable=False)
    hidden_total = Column(Integer, default=0, server_default="0", nullable=False)
    sandbox = Column(String(20), default="", server_default="", nullable=False)  # docker | local

    user = relationship("User", back_populates="coding_submissions")
    question = relationship("CodingQuestion", back_populates="submissions")


class CodingAssessment(Base):
    """A timed coding interview: a fixed set of problems that must be finished before a deadline."""
    __tablename__ = "coding_assessments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), default="Coding interview")
    question_ids = Column(Text, default="[]")  # JSON list
    duration_seconds = Column(Integer, nullable=False)
    started_at = Column(DateTime, default=dt.datetime.utcnow)
    deadline = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="in_progress")  # in_progress | completed | expired
    score = Column(Float, nullable=True)
    company_slug = Column(String(50), default="")
