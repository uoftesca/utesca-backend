"""
Public-facing registration endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status

from .models import (
    FileDeleteRequest,
    FileDeleteResponse,
    FileUploadRequest,
    FileUploadResponse,
    RegistrationCreateRequest,
    RsvpConfirmResponse,
    RsvpDetailsResponse,
)
from .service import RegistrationService
from utils.rate_limit import rate_limit

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

    return {
        "success": True,
        "registration_id": str(registration.id),
        "message": "Registration submitted successfully. We'll review your application and be in touch soon!",
    }


@router.get(
    "/rsvp/{token}",
    status_code=status.HTTP_200_OK,
    response_model=RsvpDetailsResponse,
)
async def rsvp_details(
    token: str,
    _rl: None = Depends(rate_limit("public_rsvp_view", limit=20, window_seconds=60)),
    service: RegistrationService = Depends(get_registration_service),
):
    registration, event = service.rsvp_details(token)
    return {
        "event": {
            "title": event.title,
            "date_time": event.date_time,
            "location": event.location,
            "description": event.description,
        },
        "registration": {
            "status": registration.status,
            "submitted_at": registration.submitted_at,
            "confirmed_at": registration.confirmed_at,
        },
        "already_confirmed": registration.status == "confirmed",
    }


@router.post(
    "/rsvp/{token}/confirm",
    status_code=status.HTTP_200_OK,
    response_model=RsvpConfirmResponse,
)
async def confirm_rsvp(
    token: str,
    service: RegistrationService = Depends(get_registration_service),
    _rl: None = Depends(rate_limit("public_rsvp_confirm", limit=10, window_seconds=60)),
):
    _, event = service.rsvp_confirm(token)
    return {
        "success": True,
        "message": "Attendance confirmed! We look forward to seeing you.",
        "event": {
            "title": event.title if event else None,
            "date_time": event.date_time if event else None,
            "location": event.location if event else None,
        },
    }

