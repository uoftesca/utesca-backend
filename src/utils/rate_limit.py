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


def _get_path(request: Request) -> str:
    return request.scope.get("path") or "unknown"


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


def rate_limit(bucket: str | None = None, limit: int = 10, window_seconds: int = 60, public: bool = False):
    """
    Dependency factory for rate limiting.

    Args:
        bucket: logical bucket name (e.g., "public_register")
        limit: max requests allowed in the window
        window_seconds: rolling window size in seconds
        public: whether authentication should NOT be attempted
    """
    if public:

        async def _enforce(request: Request):
            active_bucket = bucket or _get_path(request)
            key = _get_ip(request)

            _update_requests(active_bucket, limit, window_seconds, key)

        return _enforce
    else:

        async def _enforce_private(request: Request, user_id: UUID | None = Depends(get_optional_user_id)):
            active_bucket = bucket or _get_path(request)
            key = user_id or _get_ip(request)

            _update_requests(active_bucket, limit, window_seconds, key)

        return _enforce_private


def light_rate_limit(bucket: str | None = None, public: bool = False):
    """
    Dependency factory for light rate limiting.

    Args:
        bucket: logical bucket name (e.g., "public_register")
        public: whether authentication should NOT be attempted
    """
    return rate_limit(bucket=bucket, limit=60, public=public)


def medium_rate_limit(bucket: str | None = None, public: bool = False):
    """
    Dependency factory for medium rate limiting.

    Args:
        bucket: logical bucket name (e.g., "public_register")
        public: whether authentication should NOT be attempted
    """
    return rate_limit(bucket=bucket, limit=30, public=public)


def strict_rate_limit(bucket: str | None = None, public: bool = False):
    """
    Dependency factory for strict rate limiting.

    Args:
        bucket: logical bucket name (e.g., "public_register")
        public: whether authentication should NOT be attempted
    """
    return rate_limit(bucket=bucket, limit=10, public=public)


def harsh_rate_limit(bucket: str, public: bool = False):
    """
    Dependency factory for harsh rate limiting.

    Args:
        bucket: logical bucket name (e.g., "public_register")
        public: whether authentication should NOT be attempted
    """
    return rate_limit(bucket=bucket, limit=5, public=public)
