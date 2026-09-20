"""Short-lived JWT sessions for registration management."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from fastapi import Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel

from core.config import get_settings

ALGORITHM = "HS256"
COOKIE_NAME = "registration_session"


def get_registration_session_service() -> "RegistrationSessionService":
    """Build the configured registration session service."""
    settings = get_settings()
    if not settings.REGISTRATION_SESSION_SECRET:
        raise RuntimeError("REGISTRATION_SESSION_SECRET is not configured")
    return RegistrationSessionService(
        secret=settings.REGISTRATION_SESSION_SECRET,
        ttl_minutes=settings.REGISTRATION_SESSION_TTL_MINUTES,
        secure_cookie=settings.is_production,
    )


def require_registration_session(
    encoded_session: str | None = Cookie(default=None, alias=COOKIE_NAME),
    service: "RegistrationSessionService" = Depends(get_registration_session_service),
) -> "RegistrationSession":
    """Require a valid registration-management session cookie."""
    if not encoded_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Registration session required")
    try:
        return service.verify(encoded_session)
    except RegistrationSessionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid registration session") from exc


class RegistrationSessionError(ValueError):
    """Raised when a registration session is invalid or expired."""


class RegistrationSession(BaseModel):
    """Validated registration-management session claims."""

    registration_id: UUID
    expires_at: datetime


class RegistrationSessionService:
    """Create, validate, and transport registration-management JWTs."""

    def __init__(self, secret: str, ttl_minutes: int = 15, secure_cookie: bool = True):
        if len(secret.encode("utf-8")) < 32:
            raise ValueError("Registration session secret must be at least 32 bytes")
        if ttl_minutes <= 0:
            raise ValueError("Registration session duration must be positive")

        self.secret = secret
        self.ttl = timedelta(minutes=ttl_minutes)
        self.secure_cookie = secure_cookie

    def create(self, registration_id: UUID, expires_at: datetime | None = None) -> str:
        now = datetime.now(timezone.utc)
        session_expires_at = now + self.ttl
        if expires_at is not None:
            session_expires_at = min(session_expires_at, expires_at)
        payload = {
            "sub": str(registration_id),
            "exp": session_expires_at,
        }
        return jwt.encode(payload, self.secret, algorithm=ALGORITHM)

    def verify(self, encoded_session: str) -> RegistrationSession:
        try:
            payload = jwt.decode(
                encoded_session,
                self.secret,
                algorithms=[ALGORITHM],
                options={"require": ["sub", "exp"]},
            )
            return RegistrationSession(
                registration_id=UUID(payload["sub"]),
                expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            )
        except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
            raise RegistrationSessionError("Invalid registration session") from exc

    def set_cookie(self, response: Response, encoded_session: str) -> None:
        response.set_cookie(
            key=COOKIE_NAME,
            value=encoded_session,
            max_age=int(self.ttl.total_seconds()),
            httponly=True,
            secure=self.secure_cookie,
            samesite="lax",
            path="/",
        )

    def clear_cookie(self, response: Response) -> None:
        response.delete_cookie(
            key=COOKIE_NAME,
            httponly=True,
            secure=self.secure_cookie,
            samesite="lax",
            path="/",
        )
