"""
Repository for event registrations data access.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, cast
from uuid import UUID

from postgrest import CountMethod, ReturnMethod
from supabase import Client

from domains.events.models import EventResponse
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
        result = self.client.schema(self.schema).rpc("create_pending_event_registration", params).execute()
        if not result.data:
            raise ValueError("Failed to create pending registration")
        payload = cast(dict, result.data)
        return (
            RegistrationResponse.model_validate(payload["registration"]),
            TokenRecord.model_validate(payload["token"]),
        )

    def verify_registration(
        self,
        registration_id: UUID,
        token_hash: str,
        management_token_hash: str,
        ticket_token_hash: str,
        management_before_hours: int,
        ticket_after_hours: int,
    ) -> Tuple[RegistrationResponse, EventResponse]:
        params: Dict[str, Any] = {
            "p_registration_id": str(registration_id),
            "p_token_hash": token_hash,
            "p_management_token_hash": management_token_hash,
            "p_ticket_token_hash": ticket_token_hash,
            "p_management_before_hours": management_before_hours,
            "p_ticket_after_hours": ticket_after_hours,
        }
        result = self.client.schema(self.schema).rpc("verify_event_registration", params).execute()
        if not result.data:
            raise ValueError("Failed to verify registration")
        payload = cast(dict, result.data)
        return (
            RegistrationResponse.model_validate(payload["registration"]),
            EventResponse.model_validate(payload["event"]),
        )

    def accept_registration(
        self,
        registration_id: UUID,
        reviewer_id: UUID,
        rsvp_token_hash: str,
    ) -> Tuple[RegistrationResponse, EventResponse, TokenRecord]:
        result = (
            self.client.schema(self.schema)
            .rpc(
                "accept_event_registration",
                {
                    "p_registration_id": str(registration_id),
                    "p_reviewer_id": str(reviewer_id),
                    "p_rsvp_token_hash": rsvp_token_hash,
                },
            )
            .execute()
        )
        if not result.data:
            raise ValueError("Failed to accept registration")
        payload = cast(dict, result.data)
        return (
            RegistrationResponse.model_validate(payload["registration"]),
            EventResponse.model_validate(payload["event"]),
            TokenRecord.model_validate(payload["token"]),
        )

    def confirm_rsvp(
        self,
        registration_id: UUID,
        rsvp_token_hash: str,
        management_token_hash: str,
        ticket_token_hash: str,
        management_before_hours: int,
        ticket_after_hours: int,
    ) -> Tuple[RegistrationResponse, EventResponse]:
        params: Dict[str, Any] = {
            "p_registration_id": str(registration_id),
            "p_rsvp_token_hash": rsvp_token_hash,
            "p_management_token_hash": management_token_hash,
            "p_ticket_token_hash": ticket_token_hash,
            "p_management_before_hours": management_before_hours,
            "p_ticket_after_hours": ticket_after_hours,
        }
        result = self.client.schema(self.schema).rpc("confirm_event_rsvp", params).execute()
        if not result.data:
            raise ValueError("Failed to confirm RSVP")
        payload = cast(dict, result.data)
        return (
            RegistrationResponse.model_validate(payload["registration"]),
            EventResponse.model_validate(payload["event"]),
        )

    def get_management_token_id(self, registration_id: UUID) -> Optional[UUID]:
        result = (
            self.client.schema(self.schema)
            .table("event_registrations")
            .select("management_token")
            .eq("id", str(registration_id))
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        payload = cast(dict, result.data[0])
        if not payload.get("management_token"):
            return None
        return UUID(payload["management_token"])

    def withdraw_registration(self, registration_id: UUID) -> RegistrationResponse:
        result = (
            self.client.schema(self.schema)
            .rpc("withdraw_event_registration", {"p_registration_id": str(registration_id)})
            .execute()
        )
        if not result.data:
            raise ValueError("Failed to withdraw registration")
        return RegistrationResponse.model_validate(result.data)

    def decline_rsvp(
        self,
        registration_id: UUID,
    ) -> Tuple[RegistrationResponse, EventResponse, str]:
        result = (
            self.client.schema(self.schema)
            .rpc("decline_event_rsvp", {"p_registration_id": str(registration_id)})
            .execute()
        )
        if not result.data:
            raise ValueError("Failed to decline RSVP")
        payload = cast(dict, result.data)
        return (
            RegistrationResponse.model_validate(payload["registration"]),
            EventResponse.model_validate(payload["event"]),
            str(payload["previous_status"]),
        )

    def check_in_ticket(
        self,
        registration_id: UUID,
        ticket_token_hash: str,
        checked_in_by: UUID,
    ) -> RegistrationResponse:
        result = (
            self.client.schema(self.schema)
            .rpc(
                "check_in_event_registration",
                {
                    "p_registration_id": str(registration_id),
                    "p_ticket_token_hash": ticket_token_hash,
                    "p_checked_in_by": str(checked_in_by),
                },
            )
            .execute()
        )
        if not result.data:
            raise ValueError("Failed to check in registration")
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
