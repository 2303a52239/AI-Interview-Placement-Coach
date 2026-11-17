from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class CodingQuestionOut(BaseModel):
    id: int
    title: str
    problem_statement: str
    input_format: str
    output_format: str
    constraints: str
    sample_input: str
    sample_output: str
    difficulty: str
    topic_tag: str
    starter_code: str = ""
    starter_codes: Dict[str, str] = {}
    time_limit_seconds: int = 0
    company_tags: List[str] = []
    visible_tests: int = 0
    hidden_tests: int = 0


class CodeSubmitRequest(BaseModel):
    question_id: int
    source_code: str = Field(max_length=100_000)
    language: str = Field(default="java", pattern="^(python|java|cpp)$")
    assessment_id: Optional[int] = None


class TestCaseResult(BaseModel):
    input: str = ""
    expected_output: str = ""
    actual_output: str = ""
    passed: bool
    hidden: bool = False
    status: str = ""
    time_ms: float = 0.0


class CodeSubmitResponse(BaseModel):
    submission_id: int
    status: str
    language: str = "java"
    compile_output: str
    passed_test_cases: int
    total_test_cases: int
    hidden_passed: int = 0
    hidden_total: int = 0
    execution_time_ms: float
    time_complexity_estimate: str
    space_complexity_estimate: str
    complexity_note: str = ""
    score: float
    ai_feedback: str
    sandbox: str = ""
    test_case_results: List[TestCaseResult]


class CodeRunResponse(BaseModel):
    status: str
    compile_output: str
    sample_input: str
    expected_output: str
    actual_output: str
    passed: bool
    execution_time_ms: float
    language: str = "java"
    sandbox: str = ""


class SubmissionListItem(BaseModel):
    id: int
    question_id: int
    question_title: str
    language: str
    status: str
    score: float
    passed_test_cases: int
    total_test_cases: int
    execution_time_ms: float
    submitted_at: datetime


class SubmissionDetail(SubmissionListItem):
    source_code: str
    compile_output: str
    ai_feedback: str
    time_complexity_estimate: str
    space_complexity_estimate: str


class AssessmentStart(BaseModel):
    num_questions: int = Field(default=2, ge=1, le=5)
    duration_minutes: int = Field(default=45, ge=5, le=180)
    difficulty: Optional[str] = Field(default=None, pattern="^(easy|medium|hard)$")
    company: Optional[str] = Field(default=None, max_length=50)


class AssessmentOut(BaseModel):
    id: int
    title: str
    status: str
    duration_seconds: int
    remaining_seconds: int
    started_at: datetime
    deadline: datetime
    score: Optional[float] = None
    questions: List[CodingQuestionOut]
    best_scores: Dict[int, float] = {}
