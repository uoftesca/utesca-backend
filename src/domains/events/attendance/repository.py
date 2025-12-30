"""
Repository for attendance-related operations on event_registrations.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from supabase import Client

from domains.events.registrations.models import RegistrationResponse


class AttendanceRepository:
    """Data access for check-in operations."""

    def __init__(self, client: Client, schema: str):
        self.client = client
        self.schema = schema

    def check_in(
        self, registration_id: UUID, checked_in_by: UUID, checked_in_at: datetime
    ) -> Optional[RegistrationResponse]:
        result = (
            self.client.schema(self.schema)
            .table("event_registrations")
            .update(
                {
                    "checked_in": True,
                    "checked_in_at": checked_in_at.isoformat(),
                    "checked_in_by": str(checked_in_by),
                }
            )
            .eq("id", str(registration_id))
            .in_("status", ["accepted", "confirmed"])
            .eq("checked_in", False)
            .select("*")
            .execute()
        )
        if not result.data:
            return None
        return RegistrationResponse.model_validate(result.data[0])

    def bulk_check_in(
        self, registration_ids: List[UUID], checked_in_by: UUID, checked_in_at: datetime
    ) -> List[RegistrationResponse]:
        if not registration_ids:
            return []

        result = (
            self.client.schema(self.schema)
            .table("event_registrations")
            .update(
                {
                    "checked_in": True,
                    "checked_in_at": checked_in_at.isoformat(),
                    "checked_in_by": str(checked_in_by),
                }
            )
            .in_("id", [str(rid) for rid in registration_ids])
            .in_("status", ["accepted", "confirmed"])
            .eq("checked_in", False)
            .select("*")
            .execute()
        )

        return [RegistrationResponse.model_validate(item) for item in result.data or []]

    def get_check_in_stats(self, event_id: UUID) -> dict:
        # Simple aggregation using Supabase query; for heavy use, add an RPC.
        result = (
            self.client.schema(self.schema)
            .table("event_registrations")
            .select("status, checked_in")
            .eq("event_id", str(event_id))
            .execute()
        )
        submitted = accepted = rejected = confirmed = checked_in = 0
        for row in result.data or []:
            status = row.get("status")
            if status == "submitted":
                submitted += 1
            elif status == "accepted":
                accepted += 1
            elif status == "rejected":
                rejected += 1
            elif status == "confirmed":
                confirmed += 1
            if row.get("checked_in"):
                checked_in += 1
        total = submitted + accepted + rejected + confirmed
        return {
            "total": total,
            "submitted": submitted,
            "accepted": accepted,
            "rejected": rejected,
            "confirmed": confirmed,
            "checked_in": checked_in,
        }

