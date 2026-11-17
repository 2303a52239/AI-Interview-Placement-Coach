"""Rubric scoring shared by every provider.

`score_rubric` is the deterministic, rule-based scorer used by the mock provider (key-point coverage, ideal-answer
overlap, structure and delivery heuristics). `normalize_rubric` validates / clamps LLM output and recomputes the
weighted overall so a model can never return an inconsistent score."""
import math
import re
from collections import Counter
from typing import Any, Dict, List

from app.ai.prompts import RUBRIC_CRITERIA

STOP = set("""a an the and or of to in on for with is are was were be been it this that these those as at by from
what which how why when do does did can could should would will you your i we they he she them his her their our not no
if then than so such into about over under also very more most some any each other there here its it's""".split())
FILLERS = ["um", "uh", "like", "you know", "basically", "actually", "literally", "sort of", "kind of", "i mean"]
STRUCTURE_MARKERS = ["first", "second", "then", "because", "therefore", "for example", "for instance", "trade-off",
                     "tradeoff", "complexity", "edge case", "however", "in contrast", "whereas", "which means",
                     "as a result", "so that", "compared", "versus", "advantage", "disadvantage"]


def _stem(w: str) -> str:
    for suf in ("ing", "ed", "es", "s", "ly"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def tokens(text: str) -> List[str]:
    return [_stem(w) for w in re.findall(r"[a-zA-Z][a-zA-Z0-9+#_\-]*", (text or "").lower()) if w not in STOP and len(w) > 1]


def _cosine(a: List[str], b: List[str]) -> float:
    ca, cb = Counter(a), Counter(b)
    if not ca or not cb:
        return 0.0
    dot = sum(ca[k] * cb.get(k, 0) for k in ca)
    return dot / (math.sqrt(sum(v * v for v in ca.values())) * math.sqrt(sum(v * v for v in cb.values())))


def covered_points(answer: str, key_points: List[Dict[str, Any]]):
    """key_points: [{"label": str, "terms": [str]}]. A point is covered when any of its terms appears."""
    low = (answer or "").lower()
    toks = set(tokens(answer))
    covered, missing = [], []
    for kp in key_points:
        terms = kp.get("terms") or [kp.get("label", "")]
        hit = False
        for t in terms:
            t = t.lower().strip()
            if not t:
                continue
            if " " in t or "-" in t:
                hit = t in low
            else:
                hit = _stem(t) in toks or t in low
            if hit:
                break
        (covered if hit else missing).append(kp.get("label", terms[0] if terms else ""))
    return covered, missing


def filler_count(text: str) -> int:
    low = " " + (text or "").lower() + " "
    return sum(len(re.findall(r"(?<![a-z])" + re.escape(f) + r"(?![a-z])", low)) for f in FILLERS)


def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def overall_from(rubric: Dict[str, Dict[str, Any]]) -> float:
    total = 0.0
    for key, (weight, _d) in RUBRIC_CRITERIA.items():
        total += weight * float(rubric.get(key, {}).get("score", 0))
    return round(clamp(total), 1)


def score_rubric(question: str, answer: str, ideal_answer: str, key_points: List[Dict[str, Any]]) -> Dict[str, Any]:
    answer = (answer or "").strip()
    words = len(answer.split())
    if words == 0:
        zero = {k: {"score": 0.0, "rationale": "No answer was given."} for k in RUBRIC_CRITERIA}
        return {"rubric": zero, "score": 0.0, "covered": [], "missing": [k.get("label", "") for k in key_points],
                "words": 0, "fillers": 0}

    covered, missing = covered_points(answer, key_points)
    coverage = len(covered) / len(key_points) if key_points else None
    a_toks = tokens(answer)
    ideal_sim = _cosine(a_toks, tokens(ideal_answer)) if ideal_answer else 0.0
    q_sim = _cosine(a_toks, tokens(question))
    markers = sum(1 for m in STRUCTURE_MARKERS if m in answer.lower())
    fillers = filler_count(answer)
    sentences = max(1, len(re.findall(r"[.!?]+(?:\s|$)", answer)))

    # base signal: key-point coverage when a bank item defines them, otherwise ideal-answer similarity
    base = coverage if coverage is not None else min(1.0, ideal_sim * 1.8)
    base = 0.75 * base + 0.25 * min(1.0, ideal_sim * 1.8) if coverage is not None else base
    length_factor = min(1.0, words / 35.0)  # very short answers cannot score high

    correctness = clamp(100 * base * (0.55 + 0.45 * length_factor))
    understanding = clamp(100 * (0.7 * base + 0.3 * min(1.0, markers / 3.0)) * (0.6 + 0.4 * length_factor))
    relevance = clamp(100 * min(1.0, 0.5 * min(1.0, q_sim * 3.0) + 0.5 * min(1.0, ideal_sim * 2.5 + (coverage or 0) * 0.5)))
    completeness = clamp(100 * (coverage if coverage is not None else min(1.0, ideal_sim * 2.0)) * (0.5 + 0.5 * length_factor))

    ideal_len = 25 <= words <= 180
    comm = 55 + (20 if ideal_len else (8 if words >= 12 else -15)) + min(15, sentences * 3) - min(30, fillers * 6)
    communication = clamp(comm)
    problem_solving = clamp(100 * (0.55 * min(1.0, markers / 4.0) + 0.45 * base) * (0.6 + 0.4 * length_factor))

    def rat(label, s, hi, mid, lo):
        return hi if s >= 75 else mid if s >= 45 else lo

    rubric = {
        "correctness": {"score": round(correctness, 1), "rationale": rat("c", correctness,
            "Covers the expected concepts accurately.", "Partly covers the expected concepts.", "Little of the expected content was present.")},
        "understanding": {"score": round(understanding, 1), "rationale": rat("u", understanding,
            "Explains the why, not just the what.", "Some explanation, but mostly surface level.", "Reads as recall of terms without explanation.")},
        "relevance": {"score": round(relevance, 1), "rationale": rat("r", relevance,
            "Stays on the question asked.", "Partly addresses the question.", "Drifts away from the question.")},
        "completeness": {"score": round(completeness, 1), "rationale": (
            f"Covered {len(covered)} of {len(key_points)} expected points." if key_points else rat("p", completeness,
            "Thorough.", "Some gaps.", "Many gaps."))},
        "communication": {"score": round(communication, 1), "rationale": (
            "Clear and well sized." if communication >= 70 else
            ("Too short to judge structure." if words < 12 else "Tighten the structure" + (f" and cut {fillers} filler words." if fillers else ".")))},
        "problem_solving": {"score": round(problem_solving, 1), "rationale": rat("s", problem_solving,
            "Shows structured reasoning with examples or trade-offs.", "Some reasoning shown.", "Add reasoning steps, examples or trade-offs.")},
    }
    return {"rubric": rubric, "score": overall_from(rubric), "covered": covered, "missing": missing,
            "words": words, "fillers": fillers}


def normalize_rubric(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Validate an LLM rubric response. Raises ValueError when unusable."""
    rub = raw.get("rubric")
    if not isinstance(rub, dict):
        raise ValueError("missing rubric")
    out = {}
    for key in RUBRIC_CRITERIA:
        item = rub.get(key)
        if isinstance(item, (int, float)):
            item = {"score": item, "rationale": ""}
        if not isinstance(item, dict) or "score" not in item:
            raise ValueError(f"rubric missing {key}")
        out[key] = {"score": round(clamp(float(item["score"])), 1), "rationale": str(item.get("rationale", ""))[:400]}
    return out
