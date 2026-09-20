"""
Attendance API endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from domains.auth.dependencies import get_current_user
from domains.auth.models import UserResponse
from utils.rate_limit import medium_rate_limit

from .service import AttendanceService

router = APIRouter()


def get_attendance_service() -> AttendanceService:
    return AttendanceService()


@router.get(
    "/events/{event_id}/check-in-stats",
    status_code=status.HTTP_200_OK,
)
async def get_check_in_stats(
    event_id: UUID,
    _rl: None = Depends(medium_rate_limit("event_check_in_stats")),
    current_user: UserResponse = Depends(get_current_user),
    service: AttendanceService = Depends(get_attendance_service),
):
    return service.get_check_in_stats(event_id)
