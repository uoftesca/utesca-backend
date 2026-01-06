"""
Public-facing registration endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status

from utils.rate_limit import rate_limit

from .models import (
    FileDeleteRequest,
    FileDeleteResponse,
    FileUploadRequest,
    FileUploadResponse,
    RegistrationCreateRequest,
    RsvpConfirmResponse,
    RsvpDeclineResponse,
    RsvpDetailsByIdResponse,
    RsvpEventDetails,
    RsvpRegistrationDetails,
)
from .service import RegistrationService

router = APIRouter()


def get_registration_service() -> RegistrationService:
    return RegistrationService()


@router.post(
    "/events/{slug}/upload-file",
    status_code=status.HTTP_200_OK,
    response_model=FileUploadResponse,
)
async def upload_file(
    slug: str,
    payload: FileUploadRequest,
    _rl: None = Depends(rate_limit("public_upload_file", limit=10, window_seconds=60)),
    service: RegistrationService = Depends(get_registration_service),
):
    created = service.upload_file(event_slug=slug, payload=payload)
    return FileUploadResponse(success=True, file_id=created.id)


@router.delete(
    "/events/{slug}/upload-file/{file_id}",
    status_code=status.HTTP_200_OK,
    response_model=FileDeleteResponse,
)
async def delete_file(
    slug: str,
    file_id: UUID,
    body: FileDeleteRequest,
    _rl: None = Depends(rate_limit("public_upload_file", limit=10, window_seconds=60)),
    service: RegistrationService = Depends(get_registration_service),
):
    """
    Delete an uploaded file before registration submission.

    Body must include:
    - upload_session_id: str
    - field_name: str
    """
    upload_session_id = body.upload_session_id
    field_name = body.field_name

    service.delete_uploaded_file(
        event_slug=slug,
        file_id=file_id,
        upload_session_id=upload_session_id,
        field_name=field_name,
    )
    return FileDeleteResponse(success=True)


@router.post(
    "/events/{slug}/register",
    status_code=status.HTTP_201_CREATED,
)
async def register(
    slug: str,
    payload: RegistrationCreateRequest,
    background_tasks: BackgroundTasks,
    service: RegistrationService = Depends(get_registration_service),
    _rl: None = Depends(rate_limit("public_register", limit=5, window_seconds=60)),
):
    registration = service.submit_registration(
        event_slug=slug,
        form_data=payload.form_data,
        upload_session_id=payload.upload_session_id,
    )

    # Queue email to send after response
    event = service._get_event_or_404(slug)
    background_tasks.add_task(
        service.send_confirmation_email,
        registration=registration,
        event=event,
    )

    # Determine response message based on registration status
    message = (
        "Registration confirmed! Check your email for next steps to confirm your attendance."
        if registration.status == "accepted"
        else (
            "Registration submitted! Check your email for confirmation and updates. "
            "We'll review your application and be in touch soon."
        )
    )

    return {
        "success": True,
        "registration_id": str(registration.id),
        "message": message,
    }


@router.get(
    "/rsvp/{registration_id}",
    status_code=status.HTTP_200_OK,
    response_model=RsvpDetailsByIdResponse,
)
async def rsvp_details(
    registration_id: UUID,
    _rl: None = Depends(rate_limit("public_rsvp_view", limit=20, window_seconds=60)),
    service: RegistrationService = Depends(get_registration_service),
):
    """
    Get RSVP details.

    Returns event and registration details with metadata about allowed actions.
    Only accessible for registrations with status in ['accepted', 'confirmed', 'not_attending'].
    """
    registration, event, metadata = service.rsvp_details(registration_id)
    return RsvpDetailsByIdResponse(
        event=RsvpEventDetails(
            title=event.title,
            date_time=event.date_time,
            location=event.location,
            description=event.description,
        ),
        registration=RsvpRegistrationDetails(
            status=registration.status,
            submitted_at=registration.submitted_at,
            confirmed_at=registration.confirmed_at,
        ),
        current_status=metadata["current_status"],
        can_confirm=metadata["can_confirm"],
        can_decline=metadata["can_decline"],
        is_final=metadata["is_final"],
        event_has_passed=metadata["event_has_passed"],
        within_rsvp_cutoff=metadata["within_rsvp_cutoff"],
    )


@router.post(
    "/rsvp/{registration_id}/confirm",
    status_code=status.HTTP_200_OK,
    response_model=RsvpConfirmResponse,
)
async def confirm_rsvp(
    registration_id: UUID,
    background_tasks: BackgroundTasks,
    service: RegistrationService = Depends(get_registration_service),
    _rl: None = Depends(rate_limit("public_rsvp_confirm", limit=10, window_seconds=60)),
):
    """
    Confirm attendance.

    Validates that registration is in 'accepted' status and event hasn't passed.
    Sends confirmation email as background task.
    """
    registration = service.rsvp_confirm(registration_id)
    event = service.events_repo.get_by_id(UUID(str(registration.event_id)))

    # Queue confirmation email
    if event and registration.form_data.get("email"):
        background_tasks.add_task(
            service.send_attendance_confirmed_email,
            registration=registration,
            event=event,
        )

    return RsvpConfirmResponse(
        success=True,
        message="Attendance confirmed! We look forward to seeing you.",
        event=RsvpEventDetails(
            title=event.title if event else "",
            date_time=event.date_time if event else None,
            location=event.location if event else None,
            description=event.description if event else None,
        ),
    )


@router.post(
    "/rsvp/{registration_id}/decline",
    status_code=status.HTTP_200_OK,
    response_model=RsvpDeclineResponse,
)
async def decline_rsvp(
    registration_id: UUID,
    background_tasks: BackgroundTasks,
    service: RegistrationService = Depends(get_registration_service),
    _rl: None = Depends(rate_limit("public_rsvp_decline", limit=10, window_seconds=60)),
):
    """
    Decline attendance (set status to not_attending).

    This is a TERMINAL operation - cannot be reversed.
    Validates that registration is in 'accepted' or 'confirmed' status and event hasn't passed.
    Sends decline confirmation email as background task.
    """
    registration = service.rsvp_decline(registration_id)
    event = service.events_repo.get_by_id(UUID(str(registration.event_id)))

    # Queue decline confirmation email
    if event and registration.form_data.get("email"):
        background_tasks.add_task(
            service.send_attendance_declined_email,
            registration=registration,
            event=event,
        )

    return RsvpDeclineResponse(
        success=True,
        message=(
            f"You are no longer attending {event.title if event else 'this event'}. "
            "We have received your RSVP response. This change is final."
        ),
        final=True,
    )
