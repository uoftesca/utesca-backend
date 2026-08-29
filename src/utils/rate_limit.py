"""
Lightweight in-memory rate limiting dependency for FastAPI.

Intended for low-volume public endpoints; not suitable for multi-instance deployments
without a shared store. For production scale, replace with Redis/Cloudflare/etc.
"""

import time
from collections import deque
from typing import Deque
from uuid import UUID

from fastapi import Depends, HTTPException, status
from starlette.requests import Request

from domains.auth.dependencies import get_optional_user_id

# key: bucket -> {key: ip | uid -> deque[timestamps]}
_requests: dict[str, dict[str | UUID, Deque[float]]] = {}


def reset_rate_limits(bucket: str | None = None) -> None:
    """Testing/helper utility to clear stored counters."""
    if bucket is None:
        _requests.clear()
        return

    if bucket in _requests:
        _requests[bucket].clear()


def _get_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _update_requests(bucket: str, limit: int, window_seconds: int, key: str | UUID) -> None:
    now = time.time()
    window_start = now - window_seconds

    d = _requests.setdefault(bucket, {})
    q = d.setdefault(key, deque())

    # drop old entries
    while q and q[0] < window_start:
        q.popleft()

    if len(q) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait and try again.",
        )

    q.append(now)


def rate_limit(bucket: str, limit: int, window_seconds: int = 60, private: bool = False):
    """
    Dependency factory for rate limiting.

    Args:
        bucket: logical bucket name (e.g., "public_register")
        limit: max requests allowed in the window
        window_seconds: rolling window size in seconds
    """
    if private:

        async def _enforce_private(request: Request, user_id: UUID | None = Depends(get_optional_user_id)):
            _update_requests(bucket, limit, window_seconds, user_id or _get_ip(request))

        return _enforce_private
    else:

        async def _enforce(request: Request):
            _update_requests(bucket, limit, window_seconds, _get_ip(request))

        return _enforce
