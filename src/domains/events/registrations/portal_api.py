"""
Portal-facing registration endpoints (authenticated).
"""

import csv
import io
from datetime import datetime, timezone
from typing import Dict, List, Optional
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
    Update registration status (accept, reject, or waitlist application).

    VPs and Co-Presidents can update application status.
    Email notifications are sent for accept and reject actions only:
    - Acceptance email: includes RSVP link for attendance confirmation
    - Rejection email: polite notification with encouragement for future events
    - Waitlist: no email is sent — this is an internal action only

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

    elif payload.status == "waitlist":
        updated = service.waitlist_application(registration_id, current_user.id)
        # No email
        # Manual waitlisting is an internal action; the applicant is not notified

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

    Generates a downloadable CSV containing all registration data for the
    specified event. Supports comma-separated multi-status filtering. Includes
    all dynamic form fields, file upload URLs, and handles nested/array values.

    Returns:
        CSV file as downloadable attachment with the event slug in the filename.

    Raises:
        HTTPException: 404 if event not found
    """
    statuses: Optional[List[str]] = [s.strip() for s in status.split(",")] if status else None
    slug, rows = service.export_registrations(event_id, statuses)

    fieldnames = list(rows[0].keys()) if rows else ["Registration ID"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    csv_bytes = buf.getvalue().encode("utf-8")
    filename = f"event-registrations-{slug}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/csv",
        },
    )


@router.get(
    "/events/{event_id}/registrations/files/download",
    status_code=status.HTTP_200_OK,
)
async def download_registration_files(
    event_id: UUID,
    current_user: UserResponse = Depends(get_current_vp_or_admin),
    service: RegistrationService = Depends(get_registration_service),
):
    """
    Download all uploaded files from accepted/confirmed registrations as a ZIP.

    Each file inside the ZIP is renamed to ``lastname-firstname-fieldname.ext``.
    Duplicate names are automatically suffixed with -2, -3, etc. Files from
    rejected, submitted, or deleted registrations are excluded.

    Returns:
        ZIP file as a downloadable attachment. Includes an ``X-Download-Errors``
        header if any individual file downloads failed during archive creation.

    Raises:
        HTTPException: 404 if event not found or no files are available.
    """
    slug, zip_bytes, error_count = service.download_files_as_zip(event_id)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{slug}-files-{timestamp}.zip"

    headers: Dict[str, str] = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": "application/zip",
    }
    if error_count > 0:
        headers["X-Download-Errors"] = str(error_count)

    return Response(content=zip_bytes, media_type="application/zip", headers=headers)
