"""
OpenAIProvider - LLM-backed AIProvider using the OpenAI Chat Completions API.

* Model, base URL, timeout and retry count come from settings (OPENAI_MODEL, OPENAI_BASE_URL, ...).
* Responses are requested as JSON objects, parsed and validated; anything invalid is treated as a failure.
* Transient errors (timeouts, 429, 5xx) are retried with exponential backoff.
* Token usage from every successful call is recorded (see app.ai.usage).
* If every attempt fails the call degrades to MockAIProvider and the result is flagged `simulated=True`,
  so the UI never presents rule-based output as model output.

NOTE: this code path has not been exercised against the live OpenAI API in the development sandbox (no
network access). It is covered by tests using a stubbed HTTP transport.
"""
import json
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from app.ai import prompts, usage
from app.ai.base import AIProvider
from app.ai.mock_provider import MockAIProvider
from app.ai.rubric import normalize_rubric, overall_from
from app.config import settings

logger = logging.getLogger("ai.openai_provider")

RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}


class OpenAIProvider(AIProvider):
    name = "openai"
    simulated = False

    def __init__(self, transport: Optional[httpx.BaseTransport] = None):
        self._fallback = MockAIProvider()
        self._transport = transport  # injected in tests
        self._feature = "general"

    # ------------------------------------------------------------------ core call
    def _url(self) -> str:
        return settings.OPENAI_BASE_URL.rstrip("/") + "/chat/completions"

    def _call(self, system_prompt: str, user_prompt: str, feature: str = "general") -> Optional[Dict[str, Any]]:
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set; using mock provider.")
            return None
        body = {
            "model": settings.OPENAI_MODEL,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
        }
        headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"}
        attempts = max(1, settings.OPENAI_MAX_RETRIES + 1)
        for attempt in range(attempts):
            try:
                with httpx.Client(timeout=settings.OPENAI_TIMEOUT_SECONDS, transport=self._transport) as client:
                    resp = client.post(self._url(), headers=headers, json=body)
                if resp.status_code in RETRYABLE_STATUS and attempt < attempts - 1:
                    delay = min(8.0, 0.5 * (2 ** attempt))
                    logger.warning("OpenAI %s, retrying in %.1fs (%d/%d)", resp.status_code, delay, attempt + 1, attempts - 1)
                    time.sleep(delay)
                    continue
                resp.raise_for_status()
                data = resp.json()
                u = data.get("usage") or {}
                usage.record(feature, "openai", data.get("model", settings.OPENAI_MODEL),
                             u.get("prompt_tokens", 0), u.get("completion_tokens", 0))
                return json.loads(data["choices"][0]["message"]["content"])
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt < attempts - 1:
                    time.sleep(min(8.0, 0.5 * (2 ** attempt)))
                    continue
                logger.error("OpenAI network failure: %s", exc)
            except Exception as exc:  # noqa: BLE001 - never crash the app on AI failure
                logger.error("OpenAI call failed: %s", exc)
                return None
        return None

    @staticmethod
    def _mark(d: Dict[str, Any], simulated: bool, provider: str) -> Dict[str, Any]:
        d["simulated"] = simulated
        d["provider"] = provider
        return d

    # ------------------------------------------------------------------ original interface
    def generate_questions(self, interview_type, target_role, context, num_questions):
        result = self._call(
            "You are an expert technical/HR interviewer. Respond ONLY with JSON.",
            prompts.QUESTION_PROMPT.format(interview_type=interview_type, target_role=target_role, topic="mixed",
                                           difficulty="mixed", context=context, count=num_questions),
            "question_generation",
        )
        qs = result.get("questions") if isinstance(result, dict) else None
        if isinstance(qs, list) and qs and all(isinstance(q, dict) and q.get("question") for q in qs):
            return qs[:num_questions]
        return self._fallback.generate_questions(interview_type, target_role, context, num_questions)

    def evaluate_answer(self, interview_type, question, answer, context):
        result = self._call(
            prompts.SYSTEM_EVALUATOR + ' Keys: "score" (0-100), "strengths" (list), "weaknesses" (list), '
            '"feedback" (string), "suggested_improvement" (string).',
            f"Interview type: {interview_type}\nQuestion: {question}\nCandidate answer: {answer}\nContext: {context}",
            "answer_evaluation",
        )
        if isinstance(result, dict) and isinstance(result.get("score"), (int, float)):
            return result
        return self._fallback.evaluate_answer(interview_type, question, answer, context)

    def summarize_interview(self, interview_type, qa_pairs):
        result = self._call(prompts.SUMMARY_SYSTEM, f"Interview type: {interview_type}\nQA data: {json.dumps(qa_pairs)}",
                            "interview_summary")
        if isinstance(result, dict) and isinstance(result.get("overall_score"), (int, float)):
            return result
        return self._fallback.summarize_interview(interview_type, qa_pairs)

    def evaluate_code(self, problem_statement, source_code, passed, total, compile_ok):
        result = self._call(
            "You are a senior engineer reviewing a coding submission. Respond ONLY with JSON keys "
            '"feedback", "time_complexity_estimate", "space_complexity_estimate" (all strings).',
            f"Problem: {problem_statement}\nCode:\n{source_code}\nTests: {passed}/{total} passed. Compiled: {compile_ok}.",
            "code_review",
        )
        if isinstance(result, dict) and "feedback" in result:
            return result
        return self._fallback.evaluate_code(problem_statement, source_code, passed, total, compile_ok)

    # ------------------------------------------------------------------ advanced interface
    def evaluate_rubric(self, interview_type, topic, question, answer, ideal_answer, key_points):
        criteria = ", ".join(prompts.RUBRIC_CRITERIA)
        points = "\n".join(f"- {k.get('label')}" for k in key_points) or "(none provided)"
        raw = self._call(
            prompts.SYSTEM_EVALUATOR,
            prompts.RUBRIC_PROMPT.format(interview_type=interview_type, topic=topic, question=question,
                                         key_points=points, ideal_answer=ideal_answer or "(none)",
                                         answer=answer, criteria=criteria),
            "rubric_evaluation",
        )
        try:
            if not isinstance(raw, dict):
                raise ValueError("no response")
            rubric = normalize_rubric(raw)
            return {
                "score": overall_from(rubric), "rubric": rubric,
                "strengths": [str(x) for x in raw.get("strengths", [])][:6],
                "weaknesses": [str(x) for x in raw.get("weaknesses", [])][:6],
                "missing_points": [str(x) for x in raw.get("missing_points", [])][:8],
                "feedback": str(raw.get("feedback", "")), "suggested_improvement": str(raw.get("suggested_improvement", "")),
                "ideal_answer": str(raw.get("ideal_answer") or ideal_answer or ""),
                "provider": "openai", "simulated": False,
            }
        except (ValueError, TypeError) as exc:
            logger.warning("Invalid rubric from model (%s); using mock scorer.", exc)
            return self._fallback.evaluate_rubric(interview_type, topic, question, answer, ideal_answer, key_points)

    def generate_followup(self, interview_type, question, answer, missing_points):
        raw = self._call(prompts.SYSTEM_EVALUATOR,
                         prompts.FOLLOWUP_PROMPT.format(interview_type=interview_type, question=question, answer=answer,
                                                        missing=", ".join(missing_points) or "none"), "followup")
        if isinstance(raw, dict) and raw.get("question"):
            raw.setdefault("ideal_answer", "")
            raw.setdefault("key_points", [])
            return raw
        return self._fallback.generate_followup(interview_type, question, answer, missing_points)

    def rag_answer(self, question, passages):
        listing = "\n\n".join(f"[{i}] {p.get('content', '')}" for i, p in enumerate(passages, start=1))
        raw = self._call("Answer strictly from the provided passages. Respond ONLY with JSON.",
                         prompts.RAG_PROMPT.format(question=question, passages=listing), "rag_answer")
        if isinstance(raw, dict) and raw.get("answer"):
            return {"answer": str(raw["answer"]), "simulated": False}
        return self._fallback.rag_answer(question, passages)
