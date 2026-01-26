"""
Portal-facing registration endpoints (authenticated).
"""

import csv
import io
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status

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
    """
    List all registrations for a specific event with pagination and filtering.

    Supports filtering by status and searching by attendee name/email.
    Returns paginated results with metadata.
    """
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
    """
    Get detailed information about a specific registration.

    Returns full registration details including form data, timestamps,
    review information, check-in status, and RSVP link (if accepted).

    Raises:
        HTTPException: 404 if registration not found
    """
    registration = service.get_registration_detail(registration_id)
    return {"registration": registration}


@router.patch(
    "/registrations/{registration_id}/status",
    status_code=status.HTTP_200_OK,
)
async def update_status(
    registration_id: UUID,
    payload: RegistrationStatusUpdate,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_vp_or_admin),
    service: RegistrationService = Depends(get_registration_service),
):
    """
    Update registration status (accept or reject application).

    VPs and Co-Presidents can accept or reject pending applications.
    Automatically sends customizable email notifications to applicants as background tasks:
    - Acceptance email: includes RSVP link for attendance confirmation
    - Rejection email: polite notification with encouragement for future events

    Email templates can be customized per event using acceptance_email_template
    and rejection_email_template fields. If no custom template is provided,
    system defaults are used. Templates support variables: {{full_name}},
    {{event_title}}, {{event_datetime}}, {{event_location}}, {{rsvp_link}}.

    Email sending happens asynchronously and failures do not block the status update.

    Returns:
        Success response with updated registration and optional RSVP link

    Raises:
        HTTPException: 400 if invalid status provided
        HTTPException: 403 if user lacks VP/admin permissions
        HTTPException: 404 if registration not found
    """
    if payload.status == "accepted":
        updated = service.accept_application(registration_id, current_user.id)

        # Queue acceptance email
        event = service.events_repo.get_by_id(updated.event_id)
        if event:
            background_tasks.add_task(
                service.send_acceptance_email,
                registration=updated,
                event=event,
            )

    elif payload.status == "rejected":
        updated = service.reject_application(registration_id, current_user.id)

        # Queue rejection email
        event = service.events_repo.get_by_id(updated.event_id)
        if event:
            background_tasks.add_task(
                service.send_rejection_email,
                registration=updated,
                event=event,
            )

    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

    return {"success": True, "registration": updated}


@router.get(
    "/events/{event_id}/analytics",
    status_code=status.HTTP_200_OK,
)
async def analytics(
    event_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """
    Get comprehensive analytics for an event.

    Returns aggregated statistics including:
    - Registration counts by status
    - Confirmation and attendance rates
    - Timeline of registration activity
    - Check-in statistics

    Returns:
        EventAnalyticsResponse with all analytics data

    Raises:
        HTTPException: 404 if event not found
    """
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
    """
    Export event registrations as CSV file.

    Generates a downloadable CSV file containing all registration data
    for the specified event. Can be filtered by status. Includes:
    - Registration ID and status
    - Submission and review timestamps
    - Confirmation and check-in information
    - Attendee name and email

    Returns:
        CSV file as downloadable attachment

    Raises:
        HTTPException: 404 if event not found
    """
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
