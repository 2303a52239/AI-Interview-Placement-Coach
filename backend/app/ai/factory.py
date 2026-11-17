from functools import lru_cache

from app.ai.base import AIProvider
from app.ai.mock_provider import MockAIProvider
from app.config import settings


@lru_cache
def get_ai_provider() -> AIProvider:
    if settings.AI_PROVIDER.lower() == "openai":
        from app.ai.openai_provider import OpenAIProvider  # imported lazily
        return OpenAIProvider()
    return MockAIProvider()


def ai_status() -> dict:
    """Honest description of what is answering, exposed to the UI."""
    wants_openai = settings.AI_PROVIDER.lower() == "openai"
    live = wants_openai and bool(settings.OPENAI_API_KEY)
    return {
        "configured_provider": settings.AI_PROVIDER.lower(),
        "live_llm": live,
        "model": settings.OPENAI_MODEL if live else None,
        "mode": "openai" if live else "mock",
        "note": None if live else (
            "AI_PROVIDER=openai but OPENAI_API_KEY is empty; running in mock mode." if wants_openai else
            "Mock mode: answers are scored by deterministic rules, not by a language model."),
    }
