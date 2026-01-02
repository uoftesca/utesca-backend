"""
Attendance service layer for check-in operations.
"""

from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client, create_client

from core.config import get_settings
from core.database import get_schema
from domains.events.registrations.models import RegistrationResponse
from domains.events.registrations.repository import RegistrationsRepository
from .models import BulkCheckInResponse, BulkCheckInResult, CheckInResponse
from .repository import AttendanceRepository
from ..repository import EventRepository


class AttendanceService:
    """Business logic for attendance/check-in."""

    def __init__(self):
        settings = get_settings()
        self.schema = get_schema()
        self.supabase: Client = create_client(
            settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
        )
        self.events_repo = EventRepository(self.supabase, self.schema)
        self.reg_repo = RegistrationsRepository(self.supabase, self.schema)
        self.att_repo = AttendanceRepository(self.supabase, self.schema)

    def _get_registration_or_404(self, registration_id: UUID) -> RegistrationResponse:
        registration = self.reg_repo.get_registration_by_id(registration_id)
        if not registration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registration not found",
            )
        return registration

    def check_in_attendee(self, registration_id: UUID, checked_in_by: UUID) -> CheckInResponse:
        registration = self._get_registration_or_404(registration_id)
        if registration.status not in ("accepted", "confirmed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only accepted or confirmed registrations can be checked in",
            )

        updated = self.att_repo.check_in(
            registration_id=registration_id,
            checked_in_by=checked_in_by,
            checked_in_at=datetime.now(timezone.utc),
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already checked in or invalid status",
            )
        return CheckInResponse(
            id=updated.id,
            checked_in=updated.checked_in,
            checked_in_at=updated.checked_in_at,
            checked_in_by=updated.checked_in_by,
        )

    def bulk_check_in(self, registration_ids: List[UUID], checked_in_by: UUID) -> BulkCheckInResponse:
        # Validate existence of each registration (lightweight; can be optimized with a single query)
        for rid in registration_ids:
            reg = self.reg_repo.get_registration_by_id(rid)
            if not reg:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Registration {rid} not found",
                )
            if reg.status not in ("accepted", "confirmed"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Registration {rid} not eligible for check-in",
                )

        updated = self.att_repo.bulk_check_in(
            registration_ids=registration_ids,
            checked_in_by=checked_in_by,
            checked_in_at=datetime.now(timezone.utc),
        )
        results = [
            BulkCheckInResult(id=item.id, checked_in=item.checked_in) for item in updated
        ]
        return BulkCheckInResponse(
            checked_in_count=len(updated),
            results=results,
        )

    def get_check_in_stats(self, event_id: UUID) -> dict:
        # Ensure event exists
        event = self.events_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found",
            )
        return self.att_repo.get_check_in_stats(event_id)

