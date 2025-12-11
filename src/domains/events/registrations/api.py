"""
Public-facing registration endpoints.
"""

from typing import Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client, create_client

from core.config import get_settings
from core.database import get_schema
from domains.events.repository import EventRepository
from .files_repository import RegistrationFilesRepository
from .models import FileUploadRequest, RegistrationCreateRequest
from .repository import RegistrationsRepository
from .service import RegistrationService

router = APIRouter()

MAX_FILE_SIZE = 2_097_152  # 2MB
ALLOWED_TYPES = {"application/pdf"}


def get_admin_client() -> Client:
    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def get_repos():
    client = get_admin_client()
    schema = get_schema()
    return (
        EventRepository(client, schema),
        RegistrationFilesRepository(client, schema),
        RegistrationsRepository(client, schema),
    )


def get_registration_service() -> RegistrationService:
    return RegistrationService()


@router.post(
    "/events/{slug}/upload-file",
    status_code=status.HTTP_200_OK,
)
async def upload_file(slug: str, payload: FileUploadRequest):
    events_repo, files_repo, _ = get_repos()
    event = events_repo.get_by_slug(slug)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if payload.file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 2MB.",
        )
    if payload.mime_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed.",
        )

    created = files_repo.create_file_record(
        event_id=event.id,
        field_name=payload.field_name,
        file_url=payload.file_url,
        file_name=payload.file_name,
        file_size=payload.file_size,
        mime_type=payload.mime_type,
        upload_session_id=payload.upload_session_id,
    )
    return {"success": True, "file_id": str(created.id)}


@router.post(
    "/events/{slug}/register",
    status_code=status.HTTP_201_CREATED,
)
async def register(
    slug: str,
    payload: RegistrationCreateRequest,
    service: RegistrationService = Depends(get_registration_service),
):
    registration = service.submit_registration(
        event_slug=slug,
        form_data=payload.form_data,
        upload_session_id=payload.upload_session_id,
    )
    return {
        "success": True,
        "registration_id": str(registration.id),
        "message": "Registration submitted successfully. We'll review your application and be in touch soon!",
    }


@router.get(
    "/rsvp/{token}",
    status_code=status.HTTP_200_OK,
)
async def rsvp_details(token: str):
    events_repo, _, regs_repo = get_repos()
    registration = regs_repo.get_registration_by_rsvp_token(token)
    if not registration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid RSVP token")
    if registration.status not in ("accepted", "confirmed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration is not eligible for confirmation",
        )
    event = events_repo.get_by_id(UUID(str(registration.event_id)))
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
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
)
async def confirm_rsvp(token: str, service: RegistrationService = Depends(get_registration_service)):
    registration = service.confirm_rsvp(token)
    events_repo, _, _ = get_repos()
    event = events_repo.get_by_id(UUID(str(registration.event_id)))
    return {
        "success": True,
        "message": "Attendance confirmed! We look forward to seeing you.",
        "event": {
            "title": event.title if event else None,
            "date_time": event.date_time if event else None,
            "location": event.location if event else None,
        },
    }

