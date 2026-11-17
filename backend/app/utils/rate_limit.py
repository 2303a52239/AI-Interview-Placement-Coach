"""
Small in-memory sliding-window rate limiter (per client IP and route group).

Suitable for a single API process. With several workers/instances each keeps
its own counters; put a shared limiter (Redis, or your reverse proxy) in front
for strict global limits - see docs/DEPLOYMENT.md.
"""
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

AI_PATH_PREFIXES = ("/interviews", "/evaluate", "/rag", "/speech", "/resume", "/coding")


def _group_and_limit(path: str, method: str = "POST") -> tuple[str, int]:
    if path.startswith("/auth/login") or path.startswith("/auth/register") or path.startswith("/auth/refresh"):
        return "auth", settings.RATE_LIMIT_AUTH_PER_MINUTE
    # Only writes (submit answer, run code, upload, chat) are expensive; plain page-load GETs use the general limit.
    if path.startswith(AI_PATH_PREFIXES) and method != "GET":
        return "heavy", settings.RATE_LIMIT_AI_PER_MINUTE
    return "general", settings.RATE_LIMIT_PER_MINUTE


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._hits: dict[tuple[str, str], deque] = defaultdict(deque)
        self._lock = Lock()

    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED or request.method == "OPTIONS":
            return await call_next(request)
        group, limit = _group_and_limit(request.url.path, request.method)
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        key = (client, group)
        with self._lock:
            window = self._hits[key]
            while window and now - window[0] > 60:
                window.popleft()
            if len(window) >= limit:
                retry_after = max(1, int(60 - (now - window[0])))
                return JSONResponse(
                    status_code=429,
                    content={"detail": f"Too many requests. Please retry in {retry_after} seconds."},
                    headers={"Retry-After": str(retry_after)},
                )
            window.append(now)
        return await call_next(request)
