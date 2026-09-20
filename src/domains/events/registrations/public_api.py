"""
Public-facing registration endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status

from utils.rate_limit import medium_rate_limit, strict_rate_limit

from .models import (
    FileDeleteRequest,
    FileDeleteResponse,
    FileUploadRequest,
    FileUploadResponse,
    ManagementActionResponse,
    ManagementTokenRequest,
    RegistrationCreateRequest,
    RegistrationVerificationRequest,
    RsvpConfirmResponse,
    RsvpDeclineResponse,
    RsvpDetailsByIdResponse,
    RsvpEventDetails,
    RsvpRegistrationDetails,
    RsvpTokenRequest,
)
from .service import RegistrationService
from .session import (
    RegistrationSession,
    RegistrationSessionService,
    get_registration_session_service,
    require_registration_session,
)

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
    _rl: None = Depends(strict_rate_limit("event_upload_file", public=True)),
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
    _rl: None = Depends(strict_rate_limit("event_delete_file", public=True)),
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
    _rl: None = Depends(strict_rate_limit("event_register", public=True)),
):
    registration, verification = service.submit_registration(
        event_slug=slug,
        form_data=payload.form_data,
        upload_session_id=payload.upload_session_id,
    )

    # Queue email to send after response
    event = service._get_event_or_404(slug)
    background_tasks.add_task(
        service.send_verification_email,
        registration=registration,
        event=event,
        raw_token=verification.value,
        expires_at=verification.record.expires_at,
    )

    return {
        "success": True,
        "registration_id": str(registration.id),
        "message": "Registration submitted. Check your email to verify your identity.",
    }


@router.post(
    "/registrations/{registration_id}/verify",
    status_code=status.HTTP_200_OK,
)
async def verify_registration(
    registration_id: UUID,
    payload: RegistrationVerificationRequest,
    background_tasks: BackgroundTasks,
    service: RegistrationService = Depends(get_registration_service),
    _rl: None = Depends(strict_rate_limit("verify_event_registration", public=True)),
):
    registration, event, management_token, ticket_token = service.verify_registration(registration_id, payload.token)
    background_tasks.add_task(
        service.send_post_verification_email,
        registration=registration,
        event=event,
        management_token=management_token,
        ticket_token=ticket_token,
    )
    return {
        "success": True,
        "status": registration.status,
        "message": "Email verified successfully.",
    }


@router.post(
    "/registrations/{registration_id}/management-session",
    status_code=status.HTTP_200_OK,
)
async def create_management_session(
    registration_id: UUID,
    payload: ManagementTokenRequest,
    response: Response,
    service: RegistrationService = Depends(get_registration_service),
    session_service: RegistrationSessionService = Depends(get_registration_session_service),
    _rl: None = Depends(strict_rate_limit("create_registration_management_session", public=True)),
):
    """Exchange a reusable management token for a short-lived session cookie."""
    management_token, registration = service.verify_management_token(registration_id, payload.token)
    session_service.set_cookie(
        response,
        session_service.create(registration_id, expires_at=management_token.expires_at),
    )
    return {"success": True, "registration": registration.model_dump(mode="json", by_alias=True)}


@router.post(
    "/registrations/{registration_id}/withdraw",
    status_code=status.HTTP_200_OK,
    response_model=ManagementActionResponse,
)
async def withdraw_registration(
    registration_id: UUID,
    response: Response,
    registration_session: RegistrationSession = Depends(require_registration_session),
    session_service: RegistrationSessionService = Depends(get_registration_session_service),
    service: RegistrationService = Depends(get_registration_service),
    _rl: None = Depends(strict_rate_limit("withdraw_event_registration", public=True)),
):
    if registration_session.registration_id != registration_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Registration session does not match")

    registration = service.withdraw_registration(registration_id)
    session_service.clear_cookie(response)
    return ManagementActionResponse(
        success=True,
        status=registration.status,
        message="Application withdrawn.",
    )


@router.get(
    "/rsvp/{registration_id}",
    status_code=status.HTTP_200_OK,
    response_model=RsvpDetailsByIdResponse,
)
async def rsvp_details(
    registration_id: UUID,
    _rl: None = Depends(medium_rate_limit("get_event_rsvp_details", public=True)),
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
    payload: RsvpTokenRequest,
    background_tasks: BackgroundTasks,
    service: RegistrationService = Depends(get_registration_service),
    _rl: None = Depends(strict_rate_limit("confirm_event_rsvp", public=True)),
):
    """
    Confirm attendance.

    Consumes the one-time RSVP token, rotates management access, and creates
    the ticket token atomically. Sends the e-ticket as a background task.
    """
    registration, event, management_token, ticket_token = service.rsvp_confirm(
        registration_id,
        payload.token,
    )

    background_tasks.add_task(
        service.send_post_verification_email,
        registration=registration,
        event=event,
        management_token=management_token,
        ticket_token=ticket_token,
    )

    return RsvpConfirmResponse(
        success=True,
        message="Attendance confirmed! We look forward to seeing you.",
        event=RsvpEventDetails(
            title=event.title,
            date_time=event.date_time,
            location=event.location,
            description=event.description,
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
    response: Response,
    registration_session: RegistrationSession = Depends(require_registration_session),
    session_service: RegistrationSessionService = Depends(get_registration_session_service),
    service: RegistrationService = Depends(get_registration_service),
    _rl: None = Depends(strict_rate_limit("decline_event_rsvp", public=True)),
):
    """
    Decline attendance (set status to not_attending).

    This is a terminal operation authorized by the registration management session.
    """
    if registration_session.registration_id != registration_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Registration session does not match")

    registration, previous_status, event = service.rsvp_decline(registration_id)
    session_service.clear_cookie(response)

    # Queue unified notification handler (handles all email logic)
    background_tasks.add_task(
        service.handle_decline_notifications,
        registration_id=registration.id,
        previous_status=previous_status,
    )

    return RsvpDeclineResponse(
        success=True,
        status=registration.status,
        message=(
            f"You are no longer attending {event.title if event else 'this event'}. "
            "We have received your RSVP response. This change is final."
        ),
        final=True,
    )
