"""Models shared by the token repository and service."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TokenRecord(BaseModel):
    """Stored token metadata. The raw token is never persisted."""

    id: UUID
    type: str
    token_hash: str
    expires_at: datetime
    used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None
    last_verified_at: Optional[datetime] = None
    verification_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IssuedToken(BaseModel):
    """A newly generated raw token and its stored database record."""

    value: str
    record: TokenRecord
