"""Voice answer analysis computed from the transcript and timing measured in the browser."""
import re
from typing import Dict, List, Optional

from app.ai.rubric import FILLERS

SINGLE_FILLERS = ["um", "uh", "umm", "uhh", "like", "basically", "actually", "literally"]
PHRASE_FILLERS = ["you know", "sort of", "kind of", "i mean"]


def analyze_speech(transcript: str, duration_seconds: Optional[float], pauses: Optional[List[float]] = None) -> Dict:
    text = (transcript or "").lower()
    words = re.findall(r"[a-z']+", text)
    total = len(words)
    counts: Dict[str, int] = {}
    for f in SINGLE_FILLERS:
        n = sum(1 for w in words if w == f)
        if n:
            counts[f] = n
    for f in PHRASE_FILLERS:
        n = len(re.findall(r"\b" + re.escape(f) + r"\b", text))
        if n:
            counts[f] = n
    filler_total = sum(counts.values())
    wpm = round(total / (duration_seconds / 60.0), 1) if duration_seconds and duration_seconds >= 3 and total else None
    long_pauses = [p for p in (pauses or []) if p >= 1.5]

    feedback: List[str] = []
    if wpm is None:
        feedback.append("Speaking pace could not be measured (no duration recorded).")
    elif wpm < 110:
        feedback.append(f"Your pace was {wpm} words/min, slower than the 120-160 range that sounds natural. Try to keep momentum.")
    elif wpm > 175:
        feedback.append(f"Your pace was {wpm} words/min, faster than the comfortable 120-160 range. Slow down and pause between ideas.")
    else:
        feedback.append(f"Your pace of {wpm} words/min is in the comfortable 120-160 range.")
    ratio = filler_total / total if total else 0
    if filler_total == 0:
        feedback.append("No filler words detected.")
    elif ratio > 0.05:
        top = max(counts, key=counts.get)
        feedback.append(f"{filler_total} filler words ({round(100 * ratio, 1)}% of speech), most often '{top}'. Replace them with a short silent pause.")
    else:
        feedback.append(f"{filler_total} filler word(s); this is within a normal range.")
    if len(long_pauses) >= 3:
        feedback.append(f"{len(long_pauses)} long pauses (1.5s or more). Outline your answer in your head first, then speak in steady sentences.")
    elif pauses:
        feedback.append("Pauses were brief and natural.")
    return {"words": total, "duration_seconds": duration_seconds, "wpm": wpm, "filler_total": filler_total,
            "fillers": counts, "filler_ratio": round(ratio, 3), "long_pauses": len(long_pauses),
            "pause_count": len(pauses or []), "feedback": feedback}
