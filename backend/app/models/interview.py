import datetime as dt
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class Interview(Base):
    """One interview session (HR or Technical). Timed coding sessions use CodingAssessment."""
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    interview_type = Column(String(50), nullable=False)  # "hr" | "technical"
    target_role = Column(String(255), default="")
    status = Column(String(50), default="in_progress")  # in_progress | completed
    overall_score = Column(Float, nullable=True)
    technical_score = Column(Float, nullable=True)
    communication_score = Column(Float, nullable=True)
    strengths = Column(Text, default="")
    weaknesses = Column(Text, default="")
    ai_feedback = Column(Text, default="")
    recommended_topics = Column(Text, default="")
    started_at = Column(DateTime, default=dt.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, default=0)

    # ---- adaptive engine ----
    topic = Column(String(100), default="mixed")           # a topic key or "mixed"
    adaptive = Column(Boolean, default=False, server_default="false", nullable=False)
    target_questions = Column(Integer, default=0, server_default="0", nullable=False)
    current_difficulty = Column(String(20), default="medium", server_default="medium", nullable=False)
    voice_mode = Column(Boolean, default=False, server_default="false", nullable=False)
    simulated = Column(Boolean, default=True, server_default="true", nullable=False)  # produced by the mock AI

    user = relationship("User", back_populates="interviews")
    questions = relationship("InterviewQuestion", back_populates="interview", cascade="all, delete-orphan")


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    order_index = Column(Integer, default=0)
    question_text = Column(Text, nullable=False)
    difficulty = Column(String(20), default="medium")
    skill_tag = Column(String(100), default="general")

    # ---- adaptive engine ----
    bank_id = Column(Integer, nullable=True)
    ideal_answer = Column(Text, default="")
    key_points = Column(Text, default="[]")  # JSON: [{"label": str, "terms": [str]}]
    is_followup = Column(Boolean, default=False, server_default="false", nullable=False)
    parent_question_id = Column(Integer, nullable=True)

    interview = relationship("Interview", back_populates="questions")
    answer = relationship("InterviewAnswer", back_populates="question", uselist=False, cascade="all, delete-orphan")


class InterviewAnswer(Base):
    __tablename__ = "interview_answers"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("interview_questions.id"), nullable=False)
    answer_text = Column(Text, default="")
    input_mode = Column(String(20), default="text")  # text | voice
    submitted_at = Column(DateTime, default=dt.datetime.utcnow)
    speech_metrics = Column(Text, default="")  # JSON from the voice analyzer (voice answers only)

    question = relationship("InterviewQuestion", back_populates="answer")
    evaluation = relationship("Evaluation", back_populates="answer", uselist=False, cascade="all, delete-orphan")


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    answer_id = Column(Integer, ForeignKey("interview_answers.id"), nullable=False)
    score = Column(Float, default=0)
    strengths = Column(Text, default="")
    weaknesses = Column(Text, default="")
    feedback = Column(Text, default="")
    suggested_improvement = Column(Text, default="")
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    # ---- structured rubric ----
    rubric = Column(Text, default="")        # JSON: {criterion: {score, weight, rationale}}
    ideal_answer = Column(Text, default="")
    missing_points = Column(Text, default="[]")
    provider = Column(String(30), default="mock")
    simulated = Column(Boolean, default=True, server_default="true", nullable=False)

    answer = relationship("InterviewAnswer", back_populates="evaluation")


class QuestionBankItem(Base):
    """Admin-manageable interview question bank (seeded from app/data/question_bank.py)."""
    __tablename__ = "interview_bank"

    id = Column(Integer, primary_key=True, index=True)
    interview_type = Column(String(30), nullable=False, index=True)  # hr | technical
    topic = Column(String(60), nullable=False, index=True)
    difficulty = Column(String(20), nullable=False)
    question = Column(Text, nullable=False)
    ideal_answer = Column(Text, default="")
    key_points = Column(Text, default="[]")
    source = Column(String(20), default="seed")  # seed | admin
    is_active = Column(Boolean, default=True, server_default="true", nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
