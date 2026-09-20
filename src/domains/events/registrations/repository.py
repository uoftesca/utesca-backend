"""
Repository for event registrations data access.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, cast
from uuid import UUID

from postgrest import CountMethod, ReturnMethod
from supabase import Client

from domains.tokens.models import TokenRecord

from .models import RegistrationResponse, RegistrationStatus


class RegistrationsRepository:
    """Data access layer for event_registrations table."""

    def __init__(self, client: Client, schema: str):
        self.client = client
        self.schema = schema

    def create_pending_registration(
        self,
        event_id: UUID,
        form_data: dict,
        email: str,
        upload_session_id: str,
        token_hash: str,
        token_expires_at: datetime,
    ) -> Tuple[RegistrationResponse, TokenRecord]:
        params: Dict[str, Any] = {
            "p_event_id": str(event_id),
            "p_form_data": form_data,
            "p_email": email,
            "p_upload_session_id": upload_session_id,
            "p_token_hash": token_hash,
            "p_token_expires_at": token_expires_at.isoformat(),
        }
        result = (
            self.client.schema(self.schema)
            .rpc("create_pending_event_registration", params)
            .execute()
        )
        if not result.data:
            raise ValueError("Failed to create pending registration")
        payload = cast(dict, result.data)
        return (
            RegistrationResponse.model_validate(payload["registration"]),
            TokenRecord.model_validate(payload["token"]),
        )

    def verify_registration(self, registration_id: UUID, token_hash: str) -> RegistrationResponse:
        result = (
            self.client.schema(self.schema)
            .rpc(
                "verify_event_registration",
                {
                    "p_registration_id": str(registration_id),
                    "p_token_hash": token_hash,
                },
            )
            .execute()
        )
        if not result.data:
            raise ValueError("Failed to verify registration")
        return RegistrationResponse.model_validate(result.data)

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
        statuses: Optional[List[str]],
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

        if statuses:
            query = query.in_("status", statuses)

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

    def count_by_status(self, event_id: UUID, status: str) -> int:
        """
        Return the number of registrations for an event with a specific status.
        """
        result = (
            self.client.schema(self.schema)
            .table("event_registrations")
            .select("id", count=CountMethod.exact)
            .eq("event_id", str(event_id))
            .eq("status", status)
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

    def get_oldest_waitlisted(self, event_id: UUID) -> Optional[RegistrationResponse]:
        """
        Get the oldest (first) waitlisted applicant for an event.

        Returns the registration with the earliest submitted_at timestamp
        in waitlist status, or None if no waitlisted registrations exist.
        """
        result = (
            self.client.schema(self.schema)
            .table("event_registrations")
            .select("*")
            .eq("event_id", str(event_id))
            .eq("status", "waitlist")
            .order("submitted_at", desc=False)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        return RegistrationResponse.model_validate(result.data[0])

    def count_accepted_and_confirmed(self, event_id: UUID) -> int:
        """
        Count registrations with status 'accepted' or 'confirmed'.

        This represents the current number of attendees who have either
        been accepted or have confirmed attendance.
        """
        result = (
            self.client.schema(self.schema)
            .table("event_registrations")
            .select("id", count=CountMethod.exact)
            .eq("event_id", str(event_id))
            .in_("status", ["accepted", "confirmed"])
            .execute()
        )
        return result.count or 0
