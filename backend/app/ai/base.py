"""
AIProvider abstraction.

Two concrete implementations exist:
  - MockAIProvider   : fully offline, deterministic, rule-based. Always works.
  - OpenAIProvider   : calls the OpenAI Chat Completions API. Requires OPENAI_API_KEY.

Both implement the exact same interface so the rest of the application never
needs to know which one is active. Select via AI_PROVIDER env var.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class AIProvider(ABC):
    name = "base"
    simulated = True  # True when output is produced by rules, not by a language model

    @abstractmethod
    def generate_questions(
        self,
        interview_type: str,
        target_role: str,
        context: str,
        num_questions: int,
    ) -> List[Dict[str, str]]:
        """Return a list of {"question": str, "difficulty": str, "skill_tag": str}."""
        raise NotImplementedError

    @abstractmethod
    def evaluate_answer(
        self,
        interview_type: str,
        question: str,
        answer: str,
        context: str,
    ) -> Dict[str, Any]:
        """Return {"score": float 0-100, "strengths": [...], "weaknesses": [...],
        "feedback": str, "suggested_improvement": str}."""
        raise NotImplementedError

    @abstractmethod
    def summarize_interview(
        self,
        interview_type: str,
        qa_pairs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Return {"overall_score", "technical_score", "communication_score",
        "strengths", "weaknesses", "feedback", "recommended_topics"}."""
        raise NotImplementedError

    @abstractmethod
    def evaluate_code(
        self,
        problem_statement: str,
        source_code: str,
        passed: int,
        total: int,
        compile_ok: bool,
    ) -> Dict[str, Any]:
        """Return {"feedback": str, "time_complexity_estimate": str, "space_complexity_estimate": str}."""
        raise NotImplementedError

    # ---- advanced-edition methods (concrete so older subclasses keep working) ----
    def evaluate_rubric(self, interview_type: str, topic: str, question: str, answer: str,
                        ideal_answer: str, key_points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Rubric evaluation. Return {"score", "rubric": {criterion: {score, rationale}}, "strengths",
        "weaknesses", "missing_points", "feedback", "suggested_improvement", "ideal_answer",
        "provider", "simulated"}."""
        raise NotImplementedError

    def generate_followup(self, interview_type: str, question: str, answer: str,
                          missing_points: List[str]) -> Optional[Dict[str, Any]]:
        """Return {"question", "ideal_answer", "key_points"} or None."""
        raise NotImplementedError

    def rag_answer(self, question: str, passages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Return {"answer": str, "simulated": bool}."""
        raise NotImplementedError
