import datetime as dt
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship

from app.database import Base


class PerformanceSnapshot(Base):
    """A denormalized record written after every interview/coding attempt,
    used to power dashboard charts quickly without recomputing aggregates."""
    __tablename__ = "performance"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source_type = Column(String(20), nullable=False)  # hr | technical | coding
    source_id = Column(Integer, nullable=False)  # interview_id or coding_submission_id
    score = Column(Float, default=0)
    difficulty = Column(String(20), default="medium")
    skill_tags = Column(Text, default="")  # JSON list
    recorded_at = Column(DateTime, default=dt.datetime.utcnow)

    user = relationship("User", back_populates="performance_snapshots")


class PreparationPlan(Base):
    __tablename__ = "preparation_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    generated_at = Column(DateTime, default=dt.datetime.utcnow)

    user = relationship("User", back_populates="preparation_plans")
    items = relationship("PreparationItem", back_populates="plan", cascade="all, delete-orphan")


class PreparationItem(Base):
    __tablename__ = "preparation_items"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("preparation_plans.id"), nullable=False)
    topic = Column(String(255), nullable=False)
    priority = Column(String(20), default="medium")  # high | medium | low
    recommendation = Column(Text, default="")
    suggested_practice = Column(Text, default="")
    schedule = Column(String(255), default="")  # e.g. "This week"

    plan = relationship("PreparationPlan", back_populates="items")
