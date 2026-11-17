from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


class ScoreTrendPoint(BaseModel):
    date: str
    score: float
    source_type: str


class TopicScore(BaseModel):
    topic: str
    score: float
    attempts: int


class PerformanceSummary(BaseModel):
    overall_readiness: float
    technical_score: float
    hr_score: float
    coding_score: float
    communication_score: float
    total_interviews: int
    total_coding_attempts: int
    weak_topics: List[str]
    strong_topics: List[str]
    score_trend: List[ScoreTrendPoint]
    topic_scores: List[TopicScore] = []
    recommended_topics: List[str] = []
    preparation_progress: float = 0.0


class PreparationItemOut(BaseModel):
    topic: str
    priority: str
    recommendation: str
    suggested_practice: str
    schedule: str

    class Config:
        from_attributes = True


class WeeklyScheduleDay(BaseModel):
    day: str
    focus: str
    activity: str


class PreparationPlanOut(BaseModel):
    generated_at: datetime
    items: List[PreparationItemOut]
    weekly_schedule: List[WeeklyScheduleDay] = []

    class Config:
        from_attributes = True
