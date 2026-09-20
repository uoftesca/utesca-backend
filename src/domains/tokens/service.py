"""Business logic for issuing and validating opaque tokens."""

import hmac
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from utils.tokens import generate_token, hash_token

from .models import IssuedToken, TokenRecord
from .repository import TokenRepository


class TokenValidationError(ValueError):
    """Raised when a token cannot authorize the requested operation."""


class TokenService:
    """Issue, validate, consume, and revoke opaque bearer tokens."""

    def __init__(self, repository: TokenRepository):
        self.repository = repository

    def issue(self, token_type: str, expires_at: datetime) -> IssuedToken:
        if not token_type.strip():
            raise ValueError("Token type cannot be empty")
        if expires_at.tzinfo is None:
            raise ValueError("Token expiration must include a timezone")
        if expires_at <= datetime.now(timezone.utc):
            raise ValueError("Token expiration must be in the future")

        raw_token = generate_token()
        record = self.repository.create(
            token_type=token_type,
            token_hash=hash_token(raw_token),
            expires_at=expires_at,
        )
        return IssuedToken(value=raw_token, record=record)

    def verify(
        self,
        token_id: UUID,
        raw_token: str,
        expected_type: str,
        *,
        consume: bool,
        now: Optional[datetime] = None,
    ) -> TokenRecord:
        checked_at = now or datetime.now(timezone.utc)
        token = self.repository.get_by_id(token_id)

        if not token or not hmac.compare_digest(token.token_hash, hash_token(raw_token)):
            raise TokenValidationError("Invalid token")
        if token.type != expected_type:
            raise TokenValidationError("Invalid token")
        if token.revoked_at is not None or token.used_at is not None:
            raise TokenValidationError("Invalid token")
        if token.expires_at <= checked_at:
            raise TokenValidationError("Invalid token")

        if consume:
            updated = self.repository.consume(token.id, checked_at)
        else:
            updated = self.repository.record_verification(token, checked_at)

        if not updated:
            raise TokenValidationError("Invalid token")
        return updated

    def revoke(self, token_id: UUID, reason: Optional[str] = None) -> TokenRecord:
        revoked = self.repository.revoke(token_id, datetime.now(timezone.utc), reason)
        if not revoked:
            raise TokenValidationError("Token is already revoked or does not exist")
        return revoked
