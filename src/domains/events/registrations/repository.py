"""
Repository for event registrations data access.
"""

from datetime import datetime
from typing import List, Optional, Tuple, cast
from uuid import UUID

from postgrest import CountMethod, ReturnMethod
from postgrest.types import JSON
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
    ) -> RegistrationResponse:
        insert_data = {
            "event_id": str(event_id),
            "form_data": form_data,
            "status": status,
        }

        result = (
            self.client.schema(self.schema)
            .table("event_registrations")
            .insert(cast(JSON, insert_data), returning=ReturnMethod.representation)
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
            .select("*", count=CountMethod.exact)
            .eq("event_id", str(event_id))
        )

        if status:
            query = query.eq("status", status)

        if search:
            term = f"%{search}%"
            query = query.or_(f"form_data->>full_name.ilike.{term},form_data->>email.ilike.{term}")

        # Supabase pagination uses inclusive range
        query = query.order("submitted_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()

        total = result.count or 0
        registrations = [RegistrationResponse.model_validate(item) for item in result.data or []]
        return registrations, total

    def count_by_event(self, event_id: UUID) -> int:
        """
        Return the total number of registrations for an event.
        """
        result = (
            self.client.schema(self.schema)
            .table("event_registrations")
            .select("id", count=CountMethod.exact)
            .eq("event_id", str(event_id))
            .execute()
        )
        return result.count or 0

    def update_status(
        self,
        registration_id: UUID,
        status: RegistrationStatus,
        reviewer_id: UUID,
        reviewed_at: datetime,
    ) -> Optional[RegistrationResponse]:
        update_data = {
            "status": status,
            "reviewed_by": str(reviewer_id),
            "reviewed_at": reviewed_at.isoformat(),
        }

        result = (
            self.client.schema(self.schema)
            .table("event_registrations")
            .update(update_data, returning=ReturnMethod.representation)
            .eq("id", str(registration_id))
            .execute()
        )

        if not result.data:
            return None
        return RegistrationResponse.model_validate(result.data[0])

    def get_registration_public(self, registration_id: UUID) -> Optional[RegistrationResponse]:
        """
        Get registration for public RSVP access.
        Only returns registrations with status in ['accepted', 'confirmed', 'not_attending'].
        """
        result = (
            self.client.schema(self.schema)
            .table("event_registrations")
            .select("*")
            .eq("id", str(registration_id))
            .in_("status", ["accepted", "confirmed", "not_attending"])
            .execute()
        )
        if not result.data:
            return None
        return RegistrationResponse.model_validate(result.data[0])

    def confirm_registration(self, registration_id: UUID, confirmed_at: datetime) -> Optional[RegistrationResponse]:
        """
        Confirm registration.
        Only updates if current status is 'accepted'.
        """
        result = (
            self.client.schema(self.schema)
            .table("event_registrations")
            .update(
                {
                    "status": "confirmed",
                    "confirmed_at": confirmed_at.isoformat(),
                },
                returning=ReturnMethod.representation,
            )
            .eq("id", str(registration_id))
            .eq("status", "accepted")
            .execute()
        )
        if not result.data:
            return None
        return RegistrationResponse.model_validate(result.data[0])

    def set_not_attending(self, registration_id: UUID, declined_at: datetime) -> Optional[RegistrationResponse]:
        """
        Mark registration as not_attending (final decision).
        Can transition from 'accepted' or 'confirmed' to 'not_attending'.
        This is a terminal status - cannot be changed after.
        """
        result = (
            self.client.schema(self.schema)
            .table("event_registrations")
            .update(
                {
                    "status": "not_attending",
                    "confirmed_at": declined_at.isoformat(),  # Track when they declined
                },
                returning=ReturnMethod.representation,
            )
            .eq("id", str(registration_id))
            .in_("status", ["accepted", "confirmed"])
            .execute()
        )
        if not result.data:
            return None
        return RegistrationResponse.model_validate(result.data[0])
