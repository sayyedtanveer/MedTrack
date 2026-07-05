"""API rate limiting using slowapi with Redis backend.

Provides a per-user (authenticated) and per-IP (anonymous) rate limiter
backed by Redis.  Integrates with the SlowAPI / limits library.

Requirements: 44.1–44.5
"""
from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse

REDIS_URL = os.getenv("REDIS_URL")
STORAGE_URI = REDIS_URL or "memory://"


def get_user_id(request: Request) -> str:
    """Return the authenticated user ID for rate limiting, falling back to IP.

    Using the authenticated user ID prevents a single user from bypassing
    limits by rotating IP addresses, while still protecting unauthenticated
    endpoints by IP.
    """
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return str(user.id)
    return get_remote_address(request)


try:
    limiter = Limiter(
        key_func=get_user_id,
        default_limits=["100/minute"],
        storage_uri=STORAGE_URI,
    )
except Exception:
    limiter = Limiter(
        key_func=get_user_id,
        default_limits=["100/minute"],
        storage_uri="memory://",
    )


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Return HTTP 429 with a Retry-After header when the rate limit is hit."""
    retry_after = getattr(exc, "retry_after", 60)
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."},
        headers={"Retry-After": str(retry_after)},
    )
