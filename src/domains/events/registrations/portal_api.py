"""
Portal-facing registration endpoints (authenticated).
"""

import csv
import io
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from core.config import settings
from domains.auth.dependencies import get_current_user, get_current_vp_or_admin
from domains.auth.models import UserResponse
from domains.events.analytics.service import AnalyticsService
from domains.events.registrations.models import RegistrationStatusUpdate

from .service import RegistrationService

router = APIRouter()


def get_registration_service() -> RegistrationService:
    return RegistrationService()


def get_analytics_service() -> AnalyticsService:
    return AnalyticsService()


@router.get(
    "/events/{event_id}/registrations",
    status_code=status.HTTP_200_OK,
)
async def list_registrations(
    event_id: UUID,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_user),
    service: RegistrationService = Depends(get_registration_service),
):
    return service.list_registrations(
        event_id=event_id,
        status=status,
        page=page,
        limit=limit,
        search=search,
    )


@router.get(
    "/registrations/{registration_id}",
    status_code=status.HTTP_200_OK,
)
async def get_registration(
    registration_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    service: RegistrationService = Depends(get_registration_service),
):
    return {"registration": service.get_registration_detail(registration_id)}


@router.patch(
    "/registrations/{registration_id}/status",
    status_code=status.HTTP_200_OK,
)
async def update_status(
    registration_id: UUID,
    payload: RegistrationStatusUpdate,
    current_user: UserResponse = Depends(get_current_vp_or_admin),
    service: RegistrationService = Depends(get_registration_service),
):
    if payload.status == "accepted":
        updated = service.accept_application(registration_id, current_user.id)
    elif payload.status == "rejected":
        updated = service.reject_application(registration_id, current_user.id)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")
    rsvp_link = (
        f"{settings.BASE_URL}/rsvp/{updated.id}" if updated.status == "accepted" else None
    )
    return {"success": True, "registration": updated, "rsvp_link": rsvp_link}


@router.get(
    "/events/{event_id}/analytics",
    status_code=status.HTTP_200_OK,
)
async def analytics(
    event_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    return analytics_service.get_event_analytics(event_id)


@router.get(
    "/events/{event_id}/registrations/export",
    status_code=status.HTTP_200_OK,
)
async def export_registrations(
    event_id: UUID,
    status: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_user),
    service: RegistrationService = Depends(get_registration_service),
):
    data = service.list_registrations(event_id, status, page=1, limit=10_000, search=None)
    rows = []
    for reg in data.registrations:
        fd = reg.form_data or {}
        rows.append(
            {
                "Registration ID": reg.id,
                "Status": reg.status,
                "Submitted At": reg.submitted_at,
                "Reviewed By": reg.reviewed_by,
                "Reviewed At": reg.reviewed_at,
                "Confirmed At": reg.confirmed_at,
                "Checked In": reg.checked_in,
                "Checked In At": reg.checked_in_at,
                "Full Name": fd.get("fullName") or fd.get("full_name"),
                "Email": fd.get("email"),
            }
        )

    fieldnames = rows[0].keys() if rows else ["Registration ID"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    csv_bytes = buf.getvalue().encode("utf-8")
    filename = f"event-registrations-{event_id}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/csv",
        },
    )

