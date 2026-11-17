from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


class StartInterviewRequest(BaseModel):
    interview_type: str  # "hr" | "technical"
    num_questions: int = 5
    topic: str = "mixed"        # a technical topic key, or "mixed"
    adaptive: bool = False      # adaptive: one question at a time, difficulty follows your answers
    voice_mode: bool = False


class QuestionOut(BaseModel):
    id: int
    order_index: int
    question_text: str
    difficulty: str
    skill_tag: str
    is_followup: bool = False

    class Config:
        from_attributes = True


class InterviewStartResponse(BaseModel):
    interview_id: int
    interview_type: str
    target_role: str
    questions: List[QuestionOut]
    adaptive: bool = False
    target_questions: int = 0
    topic: str = "mixed"
    simulated: bool = True


class SubmitAnswerRequest(BaseModel):
    question_id: int
    answer_text: str
    input_mode: str = "text"  # text | voice
    duration_seconds: Optional[float] = None   # voice answers: speaking time measured in the browser
    pauses: Optional[List[float]] = None       # voice answers: pause lengths in seconds


class EvaluationOut(BaseModel):
    score: float
    strengths: List[str]
    weaknesses: List[str]
    feedback: str
    suggested_improvement: str
    rubric: dict = {}
    ideal_answer: str = ""
    missing_points: List[str] = []
    simulated: bool = True
    speech: Optional[dict] = None


class SubmitAnswerResponse(BaseModel):
    question_id: int
    evaluation: EvaluationOut
    next_question: Optional[QuestionOut] = None
    current_difficulty: str = "medium"


class InterviewCompleteResponse(BaseModel):
    interview_id: int
    overall_score: float
    technical_score: float
    communication_score: float
    strengths: List[str]
    weaknesses: List[str]
    ai_feedback: str
    recommended_topics: List[str]


class InterviewHistoryItem(BaseModel):
    id: int
    interview_type: str
    status: str
    overall_score: Optional[float]
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: int
    difficulty: str = "mixed"
    strengths: List[str] = []
    weaknesses: List[str] = []

    class Config:
        from_attributes = True


class InterviewDetailQuestion(BaseModel):
    question_text: str
    difficulty: str
    skill_tag: str
    answer_text: Optional[str] = None
    score: Optional[float] = None
    feedback: Optional[str] = None
    rubric: dict = {}
    ideal_answer: str = ""
    missing_points: List[str] = []
    is_followup: bool = False
    speech: Optional[dict] = None


class InterviewDetailResponse(BaseModel):
    id: int
    interview_type: str
    status: str
    overall_score: Optional[float]
    technical_score: Optional[float]
    communication_score: Optional[float]
    strengths: List[str]
    weaknesses: List[str]
    ai_feedback: str
    recommended_topics: List[str]
    started_at: datetime
    completed_at: Optional[datetime]
    questions: List[InterviewDetailQuestion]
    topic: str = "mixed"
    adaptive: bool = False
    simulated: bool = True
