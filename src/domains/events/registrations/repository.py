"""
Repository for event registrations data access.
"""

from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from supabase import Client

from .models import RegistrationResponse, RegistrationStatus


class RegistrationsRepository:
    """Data access layer for event_registrations table."""

    def __init__(self, client: Client, schema: str):
        self.client = client
        self.schema = schema

    def create_registration(
        self,
        event_id: UUID,
        form_data: dict,
        status: RegistrationStatus,
        rsvp_token: Optional[str] = None,
    ) -> RegistrationResponse:
        insert_data = {
            "event_id": str(event_id),
            "form_data": form_data,
            "status": status,
            "rsvp_token": rsvp_token,
        }

        result = (
            self.client.schema(self.schema)
            .table("event_registrations")
            .insert(insert_data)
            .select("*")
            .execute()
        )

        if not result.data:
            raise ValueError("Failed to create registration")

        return RegistrationResponse.model_validate(result.data[0])

    def get_registration_by_id(self, registration_id: UUID) -> Optional[RegistrationResponse]:
        result = (
            self.client.schema(self.schema)
            .table("event_registrations")
            .select("*")
            .eq("id", str(registration_id))
            .execute()
        )
        if not result.data:
            return None
        return RegistrationResponse.model_validate(result.data[0])

    def get_registration_by_rsvp_token(self, token: str) -> Optional[RegistrationResponse]:
        result = (
            self.client.schema(self.schema)
            .table("event_registrations")
            .select("*")
            .eq("rsvp_token", token)
            .execute()
        )
        if not result.data:
            return None
        return RegistrationResponse.model_validate(result.data[0])

    def list_registrations(
        self,
        event_id: UUID,
        status: Optional[str],
        page: int,
        limit: int,
        search: Optional[str],
    ) -> Tuple[List[RegistrationResponse], int]:
        offset = (page - 1) * limit
        query = (
            self.client.schema(self.schema)
            .table("event_registrations")
            .select("*", count="exact")
            .eq("event_id", str(event_id))
        )

        if status:
            query = query.eq("status", status)

        if search:
            term = f"%{search}%"
            query = query.or_(
                f"form_data->>full_name.ilike.{term},form_data->>email.ilike.{term}"
            )

        # Supabase pagination uses inclusive range
        query = query.order("submitted_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()

        total = result.count or 0
        registrations = [RegistrationResponse.model_validate(item) for item in result.data or []]
        return registrations, total

    def update_status(
        self,
        registration_id: UUID,
        status: RegistrationStatus,
        reviewer_id: UUID,
        reviewed_at: datetime,
        rsvp_token: Optional[str] = None,
    ) -> Optional[RegistrationResponse]:
        update_data = {
            "status": status,
            "reviewed_by": str(reviewer_id),
            "reviewed_at": reviewed_at.isoformat(),
        }
        if rsvp_token:
            update_data["rsvp_token"] = rsvp_token

        result = (
            self.client.schema(self.schema)
            .table("event_registrations")
            .update(update_data)
            .eq("id", str(registration_id))
            .select("*")
            .execute()
        )

        if not result.data:
            return None
        return RegistrationResponse.model_validate(result.data[0])

    def set_confirmed(self, token: str, confirmed_at: datetime) -> Optional[RegistrationResponse]:
        result = (
            self.client.schema(self.schema)
            .table("event_registrations")
            .update(
                {
                    "status": "confirmed",
                    "confirmed_at": confirmed_at.isoformat(),
                }
            )
            .eq("rsvp_token", token)
            .eq("status", "accepted")
            .select("*")
            .execute()
        )
        if not result.data:
            return None
        return RegistrationResponse.model_validate(result.data[0])

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

        id_strings = [str(rid) for rid in registration_ids]
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
            .in_("id", id_strings)
            .in_("status", ["accepted", "confirmed"])
            .eq("checked_in", False)
            .select("*")
            .execute()
        )

        return [RegistrationResponse.model_validate(item) for item in result.data or []]

