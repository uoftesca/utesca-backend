"""
Attendance API endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from domains.auth.dependencies import get_current_user
from domains.auth.models import UserResponse

from .models import BulkCheckInRequest, BulkCheckInResponse, CheckInResponse
from .service import AttendanceService

router = APIRouter()


def get_attendance_service() -> AttendanceService:
    return AttendanceService()


@router.post(
    "/registrations/{registration_id}/check-in",
    response_model=CheckInResponse,
    status_code=status.HTTP_200_OK,
)
async def check_in_attendee(
    registration_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    service: AttendanceService = Depends(get_attendance_service),
):
    return service.check_in_attendee(registration_id, current_user.id)


@router.post(
    "/registrations/bulk-check-in",
    response_model=BulkCheckInResponse,
    status_code=status.HTTP_200_OK,
)
async def bulk_check_in(
    payload: BulkCheckInRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: AttendanceService = Depends(get_attendance_service),
):
    return service.bulk_check_in(payload.registration_ids, current_user.id)


@router.get(
    "/events/{event_id}/check-in-stats",
    status_code=status.HTTP_200_OK,
)
async def get_check_in_stats(
    event_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    service: AttendanceService = Depends(get_attendance_service),
):
    return service.get_check_in_stats(event_id)
