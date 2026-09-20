"""Database access for the general-purpose tokens table."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from supabase import Client

from .models import TokenRecord


class TokenRepository:
    """Persist and update hashed opaque tokens."""

    def __init__(self, client: Client, schema: str):
        self.client = client
        self.schema = schema

    def create(self, token_type: str, token_hash: str, expires_at: datetime) -> TokenRecord:
        result = (
            self.client.schema(self.schema)
            .table("tokens")
            .insert(
                {
                    "type": token_type,
                    "token_hash": token_hash,
                    "expires_at": expires_at.isoformat(),
                }
            )
            .execute()
        )
        if not result.data:
            raise ValueError("Failed to create token")
        return TokenRecord.model_validate(result.data[0])

    def get_by_id(self, token_id: UUID) -> Optional[TokenRecord]:
        result = (
            self.client.schema(self.schema)
            .table("tokens")
            .select("*")
            .eq("id", str(token_id))
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        return TokenRecord.model_validate(result.data[0])

    def consume(self, token_id: UUID, consumed_at: datetime) -> Optional[TokenRecord]:
        result = (
            self.client.schema(self.schema)
            .table("tokens")
            .update({"used_at": consumed_at.isoformat()})
            .eq("id", str(token_id))
            .is_("used_at", "null")
            .is_("revoked_at", "null")
            .gt("expires_at", consumed_at.isoformat())
            .execute()
        )
        if not result.data:
            return None
        return TokenRecord.model_validate(result.data[0])

    def record_verification(
        self,
        token: TokenRecord,
        verified_at: datetime,
    ) -> Optional[TokenRecord]:
        result = (
            self.client.schema(self.schema)
            .table("tokens")
            .update(
                {
                    "last_verified_at": verified_at.isoformat(),
                    "verification_count": token.verification_count + 1,
                }
            )
            .eq("id", str(token.id))
            .is_("revoked_at", "null")
            .gt("expires_at", verified_at.isoformat())
            .execute()
        )
        if not result.data:
            return None
        return TokenRecord.model_validate(result.data[0])

    def revoke(self, token_id: UUID, revoked_at: datetime, reason: Optional[str] = None) -> Optional[TokenRecord]:
        result = (
            self.client.schema(self.schema)
            .table("tokens")
            .update(
                {
                    "revoked_at": revoked_at.isoformat(),
                    "revoked_reason": reason,
                }
            )
            .eq("id", str(token_id))
            .is_("revoked_at", "null")
            .execute()
        )
        if not result.data:
            return None
        return TokenRecord.model_validate(result.data[0])
