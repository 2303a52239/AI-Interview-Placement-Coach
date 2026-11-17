import datetime as dt
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Date, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), default="Placement roadmap")
    target_role = Column(String(255), default="")
    weeks = Column(Integer, default=4)
    hours_per_day = Column(Integer, default=2)
    start_date = Column(Date, nullable=False)
    status = Column(String(20), default="active")  # active | archived
    generated_at = Column(DateTime, default=dt.datetime.utcnow)
    weekly_targets = Column(Text, default="[]")  # JSON list
    basis = Column(Text, default="{}")  # JSON: the skill-gap snapshot this roadmap was generated from

    tasks = relationship("RoadmapTask", back_populates="roadmap", cascade="all, delete-orphan")


class RoadmapTask(Base):
    __tablename__ = "roadmap_tasks"

    id = Column(Integer, primary_key=True, index=True)
    roadmap_id = Column(Integer, ForeignKey("roadmaps.id"), nullable=False, index=True)
    due_date = Column(Date, nullable=False)
    week_index = Column(Integer, default=1)
    topic = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    task_type = Column(String(20), default="study")  # study | practice | revision | mock
    est_minutes = Column(Integer, default=45)
    status = Column(String(20), default="todo")  # todo | done
    completed_at = Column(DateTime, nullable=True)
    revision_of = Column(Integer, nullable=True)

    roadmap = relationship("Roadmap", back_populates="tasks")
