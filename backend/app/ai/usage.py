"""Collects LLM token usage during a request so the service layer can persist it to `token_usage`."""
import contextvars
from typing import Dict, List, Optional

_events: contextvars.ContextVar[Optional[List[Dict]]] = contextvars.ContextVar("ai_usage_events", default=None)


def record(feature: str, provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> None:
    events = _events.get()
    if events is None:
        events = []
        _events.set(events)
    events.append({"feature": feature, "provider": provider, "model": model,
                   "prompt_tokens": int(prompt_tokens or 0), "completion_tokens": int(completion_tokens or 0)})


def drain() -> List[Dict]:
    events = _events.get() or []
    _events.set([])
    return events


def persist(db, user_id: Optional[int]) -> int:
    """Write collected usage rows. Returns how many were stored. Never raises."""
    from app.models.rag import TokenUsage
    events = drain()
    try:
        for e in events:
            db.add(TokenUsage(user_id=user_id, **e))
        if events:
            db.commit()
    except Exception:  # noqa: BLE001 - usage tracking must never break a request
        db.rollback()
        return 0
    return len(events)
