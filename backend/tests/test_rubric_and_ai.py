import json
import httpx
import pytest

from app.ai.mock_provider import MockAIProvider
from app.ai.openai_provider import OpenAIProvider
from app.ai.rubric import overall_from, normalize_rubric
from app.ai import usage
from app.config import settings

KP = [{"label": "hash", "terms": ["hash"]}, {"label": "bucket", "terms": ["bucket"]}, {"label": "collision", "terms": ["collision"]}]
IDEAL = "HashMap hashes the key to a bucket and handles collisions with chaining."


def test_empty_answer_scores_zero():
    r = MockAIProvider().evaluate_rubric("technical", "java", "Explain HashMap", "", IDEAL, KP)
    assert r["score"] == 0 and r["simulated"] is True


def test_better_answers_score_higher_and_are_deterministic():
    m = MockAIProvider()
    weak = m.evaluate_rubric("technical", "java", "Explain HashMap", "It stores things.", IDEAL, KP)
    strong_text = ("A HashMap computes the hash of the key to choose a bucket, and handles each collision by chaining entries, "
                   "for example in a linked list, because that keeps lookups fast.")
    strong = m.evaluate_rubric("technical", "java", "Explain HashMap", strong_text, IDEAL, KP)
    assert strong["score"] > weak["score"] + 30
    assert strong == m.evaluate_rubric("technical", "java", "Explain HashMap", strong_text, IDEAL, KP)
    assert set(strong["rubric"]) == {"correctness", "understanding", "relevance", "completeness", "communication", "problem_solving"}
    assert weak["missing_points"]


def test_rubric_weights_sum_to_one_and_overall_is_weighted():
    rub = {k: {"score": 100} for k in ["correctness", "understanding", "relevance", "completeness", "communication", "problem_solving"]}
    assert overall_from(rub) == 100.0


def test_normalize_rubric_rejects_incomplete_model_output():
    with pytest.raises(ValueError):
        normalize_rubric({"rubric": {"correctness": {"score": 80}}})


def _provider(handler):
    return OpenAIProvider(transport=httpx.MockTransport(handler))


def _chat(content: dict):
    return {"model": "test-model", "choices": [{"message": {"content": json.dumps(content)}}],
            "usage": {"prompt_tokens": 120, "completion_tokens": 40}}


def test_openai_provider_parses_rubric_and_records_tokens(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
    rub = {k: {"score": 80, "rationale": "ok"} for k in ["correctness", "understanding", "relevance", "completeness", "communication", "problem_solving"]}
    p = _provider(lambda req: httpx.Response(200, json=_chat({"rubric": rub, "strengths": ["a"], "weaknesses": [], "feedback": "good"})))
    usage.drain()
    r = p.evaluate_rubric("technical", "java", "q", "answer", IDEAL, KP)
    assert r["simulated"] is False and r["provider"] == "openai" and r["score"] == 80.0
    ev = usage.drain()
    assert ev and ev[0]["prompt_tokens"] == 120 and ev[0]["completion_tokens"] == 40


def test_openai_provider_retries_on_429_then_succeeds(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "OPENAI_MAX_RETRIES", 2)
    monkeypatch.setattr("time.sleep", lambda s: None)
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, json={"error": "rate"})
        return httpx.Response(200, json=_chat({"answer": "Use [1]."}))
    out = _provider(handler).rag_answer("q", [{"content": "text"}])
    assert calls["n"] == 3 and out["simulated"] is False


def test_openai_failure_falls_back_to_mock_and_is_flagged_simulated(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "OPENAI_MAX_RETRIES", 0)
    r = _provider(lambda req: httpx.Response(500, json={})).evaluate_rubric("technical", "java", "q", "some answer here", IDEAL, KP)
    assert r["simulated"] is True


def test_invalid_json_from_model_falls_back(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
    p = _provider(lambda req: httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]}))
    assert p.evaluate_rubric("technical", "java", "q", "some answer", IDEAL, KP)["simulated"] is True
