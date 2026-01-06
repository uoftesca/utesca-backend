"""
Lightweight in-memory rate limiting dependency for FastAPI.

Intended for low-volume public endpoints; not suitable for multi-instance deployments
without a shared store. For production scale, replace with Redis/Cloudflare/etc.
"""

import time
from collections import deque
from typing import Deque, Dict, Tuple

from fastapi import HTTPException, status
from starlette.requests import Request

# key: (ip, bucket) -> deque[timestamps]
_requests: Dict[Tuple[str, str], Deque[float]] = {}


def reset_rate_limits(bucket: str | None = None) -> None:
    """Testing/helper utility to clear stored counters."""
    if bucket is None:
        _requests.clear()
        return
    to_delete = [key for key in _requests if key[1] == bucket]
    for key in to_delete:
        _requests.pop(key, None)


def rate_limit(bucket: str, limit: int, window_seconds: int = 60):
    """
    Dependency factory for rate limiting.

    Args:
        bucket: logical bucket name (e.g., "public_register")
        limit: max requests allowed in the window
        window_seconds: rolling window size in seconds
    """

    async def _enforce(request: Request):
        ip = request.client.host if request.client else "unknown"
        key = (ip, bucket)
        now = time.time()
        window_start = now - window_seconds

        q = _requests.get(key)
        if q is None:
            q = deque()
            _requests[key] = q

        # drop old entries
        while q and q[0] < window_start:
            q.popleft()

        if len(q) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please wait and try again.",
            )

        q.append(now)

    return _enforce
