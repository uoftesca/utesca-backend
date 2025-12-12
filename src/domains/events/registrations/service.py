"""
Business logic for event registrations.
"""

import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client, create_client
from core.config import get_settings
from core.database import get_schema
from ..models import RegistrationFormSchema
from ..repository import EventRepository
from .files_repository import RegistrationFilesRepository
from .models import (
    FileMeta,
    RegistrationListPagination,
    RegistrationListResponse,
    RegistrationResponse,
    RegistrationStatus,
    RegistrationWithFilesResponse,
    FileUploadRequest,
)
from .repository import RegistrationsRepository


REGISTRATION_NOT_FOUND = "Registration not found"


class RegistrationService:
    """Service layer for handling registration lifecycle."""

    MAX_FILE_SIZE = 2_097_152  # 2MB
    ALLOWED_TYPES = {"application/pdf"}

    def __init__(self):
        settings = get_settings()
        self.schema = get_schema()
        self.supabase: Client = create_client(
            settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
        )
        self.events_repo = EventRepository(self.supabase, self.schema)
        self.reg_repo = RegistrationsRepository(self.supabase, self.schema)
        self.files_repo = RegistrationFilesRepository(self.supabase, self.schema)
    # -------------------------------------------------------------------------
    # Validation helpers
    # -------------------------------------------------------------------------
    def _validate_text(self, field: dict, value: Any, errors: List[dict]):
        label = field.get("label", field.get("id"))
        validation = field.get("validation", {}) or {}
        if not isinstance(value, str):
            errors.append({"field": field.get("id"), "message": f"{label} must be a string"})
            return
        min_len = validation.get("minLength")
        max_len = validation.get("maxLength")
        pattern = validation.get("pattern")

        if min_len is not None and len(value) < min_len:
            errors.append({"field": field.get("id"), "message": f"{label} must be at least {min_len} characters"})
        if max_len is not None and len(value) > max_len:
            errors.append({"field": field.get("id"), "message": f"{label} must be at most {max_len} characters"})
        if pattern and not re.match(pattern, value):
            errors.append({"field": field.get("id"), "message": f"{label} is in an invalid format"})

    def _validate_choice(self, field: dict, value: Any, errors: List[dict]):
        label = field.get("label", field.get("id"))
        options = field.get("options") or []
        if not isinstance(value, str):
            errors.append({"field": field.get("id"), "message": f"{label} must be a string"})
            return
        if value not in options:
            errors.append({"field": field.get("id"), "message": f"{label} must be one of the allowed options"})

    def _validate_checkboxes(self, field: dict, value: Any, errors: List[dict]):
        label = field.get("label", field.get("id"))
        options = field.get("options") or []
        if not isinstance(value, list):
            errors.append({"field": field.get("id"), "message": f"{label} must be an array"})
            return
        invalid = [v for v in value if not isinstance(v, str) or v not in options]
        if invalid:
            errors.append({"field": field.get("id"), "message": f"{label} has invalid selections"})

    def _validate_files(self, field: dict, files: List[FileMeta], errors: List[dict]):
        label = field.get("label", field.get("id"))
        validation = field.get("validation", {}) or {}
        max_size = validation.get("maxSize")
        allowed_types = validation.get("allowedTypes")

        for file_meta in files:
            if max_size is not None and file_meta.file_size > max_size:
                errors.append(
                    {
                        "field": field.get("id"),
                        "message": f"{label} must be <= {max_size} bytes",
                    }
                )
            if allowed_types and file_meta.mime_type not in allowed_types:
                errors.append(
                    {
                        "field": field.get("id"),
                        "message": f"{label} must be one of: {', '.join(allowed_types)}",
                    }
                )

    def _is_missing_required(self, field_type: str, required: bool, value: Any, files: List[FileMeta]) -> bool:
        if not required:
            return False
        if field_type == "file":
            return not files
        return value is None or value == "" or (field_type == "checkbox" and not value)

    def validate_form_data(
        self,
        form_data: Dict[str, Any],
        form_schema: Dict[str, Any],
        files_by_field: Dict[str, List[FileMeta]],
    ) -> List[dict]:
        """Validate form_data against registration_form_schema."""
        errors: List[dict] = []
        fields = form_schema.get("fields", []) if form_schema else []

        validators = {
            "text": self._validate_text,
            "textarea": self._validate_text,
            "select": self._validate_choice,
            "radio": self._validate_choice,
            "checkbox": self._validate_checkboxes,
            "file": self._validate_files,
        }

        for field in fields:
            field_id = field.get("id")
            field_type = field.get("type")
            required = field.get("required", False)
            value = form_data.get(field_id)
            files = files_by_field.get(field_id, [])

            if self._is_missing_required(field_type, required, value, files):
                errors.append({"field": field_id, "message": "This field is required"})
                continue

            if value is None and not files:
                continue

            validator = validators.get(field_type)
            if validator:
                validator(field, files if field_type == "file" else value, errors)

        return errors

    # -------------------------------------------------------------------------
    # Core operations
    # -------------------------------------------------------------------------
    def _get_event_or_404(self, slug: str):
        event = self.events_repo.get_by_slug(slug)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found",
            )
        if event.status != "published":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration is not open for this event",
            )
        return event

    def _enforce_deadline(self, event):
        if not event.registration_deadline:
            return
        now = datetime.now(timezone.utc)
        deadline = (
            event.registration_deadline
            if event.registration_deadline.tzinfo
            else event.registration_deadline.replace(tzinfo=timezone.utc)
        )
        if now > deadline:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration deadline has passed for this event.",
            )

    def submit_registration(
        self, event_slug: str, form_data: Dict[str, Any], upload_session_id: str
    ) -> RegistrationResponse:
        event = self._get_event_or_404(event_slug)
        self._enforce_deadline(event)

        form_schema_model: RegistrationFormSchema = (
            event.registration_form_schema or RegistrationFormSchema()
        )
        form_schema = form_schema_model.model_dump()
        files = self.files_repo.get_files_by_upload_session(upload_session_id)
        files_by_field: Dict[str, List[FileMeta]] = defaultdict(list)
        for file_meta in files:
            files_by_field[file_meta.field_name].append(file_meta)

        errors = self.validate_form_data(form_data, form_schema, files_by_field)
        if errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Validation failed", "details": errors},
            )

        auto_accept = bool(form_schema.get("auto_accept"))
        status_value: RegistrationStatus = "accepted" if auto_accept else "submitted"
        rsvp_token = str(uuid.uuid4()) if auto_accept else None

        registration = self.reg_repo.create_registration(
            event_id=event.id,
            form_data=form_data,
            status=status_value,
            rsvp_token=rsvp_token,
        )

        # Link files after successful creation
        self.files_repo.link_files_to_registration(
            upload_session_id=upload_session_id,
            registration_id=registration.id,
            event_date=event.date_time,
        )

        return registration

    def upload_file(self, event_slug: str, payload: FileUploadRequest) -> FileMeta:
        event = self._get_event_or_404(event_slug)

        if payload.file_size > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File too large. Maximum size is 2MB.",
            )
        if payload.mime_type not in self.ALLOWED_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are allowed.",
            )

        created = self.files_repo.create_file_record(
            event_id=event.id,
            field_name=payload.field_name,
            file_url=payload.file_url,
            file_name=payload.file_name,
            file_size=payload.file_size,
            mime_type=payload.mime_type,
            upload_session_id=payload.upload_session_id,
        )
        return created

    def delete_uploaded_file(
        self, event_slug: str, file_id: UUID, upload_session_id: str, field_name: str
    ) -> None:
        event = self._get_event_or_404(event_slug)
        file_meta = self.files_repo.get_file_by_id(file_id)
        if not file_meta:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        if str(file_meta.event_id) != str(event.id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File event mismatch")
        if file_meta.upload_session_id != upload_session_id or file_meta.field_name != field_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File does not match session or field",
            )

        self.files_repo.delete_file_by_id(file_id)

    def rsvp_details(self, token: str):
        registration = self.reg_repo.get_registration_by_rsvp_token(token)
        if not registration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Invalid RSVP token"
            )
        if registration.status not in ("accepted", "confirmed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration is not eligible for confirmation",
            )
        event = self.events_repo.get_by_id(UUID(str(registration.event_id)))
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
            )
        return registration, event

    def rsvp_confirm(self, token: str):
        registration = self.reg_repo.get_registration_by_rsvp_token(token)
        if not registration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Invalid RSVP token"
            )
        if registration.status not in ("accepted", "confirmed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration is not eligible for confirmation",
            )
        updated = self.confirm_rsvp(token)
        event = self.events_repo.get_by_id(UUID(str(updated.event_id)))
        return updated, event

    def accept_application(self, registration_id: UUID, reviewer_id: UUID) -> RegistrationResponse:
        registration = self.reg_repo.get_registration_by_id(registration_id)
        if not registration:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=REGISTRATION_NOT_FOUND)
        if registration.status != "submitted":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only submitted registrations can be accepted",
            )

        rsvp_token = registration.rsvp_token or str(uuid.uuid4())
        updated = self.reg_repo.update_status(
            registration_id=registration_id,
            status="accepted",
            reviewer_id=reviewer_id,
            reviewed_at=datetime.now(timezone.utc),
            rsvp_token=rsvp_token,
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update status")
        return updated

    def reject_application(self, registration_id: UUID, reviewer_id: UUID) -> RegistrationResponse:
        registration = self.reg_repo.get_registration_by_id(registration_id)
        if not registration:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=REGISTRATION_NOT_FOUND)
        if registration.status != "submitted":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only submitted registrations can be rejected",
            )
        updated = self.reg_repo.update_status(
            registration_id=registration_id,
            status="rejected",
            reviewer_id=reviewer_id,
            reviewed_at=datetime.now(timezone.utc),
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update status")
        return updated

    def confirm_rsvp(self, token: str) -> RegistrationResponse:
        registration = self.reg_repo.get_registration_by_rsvp_token(token)
        if not registration:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid RSVP token")
        if registration.status == "confirmed":
            return registration
        if registration.status != "accepted":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration is not eligible for confirmation",
            )
        updated = self.reg_repo.set_confirmed(token, confirmed_at=datetime.now(timezone.utc))
        if not updated:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to confirm RSVP")
        return updated

    def list_registrations(
        self,
        event_id: UUID,
        status: Optional[str],
        page: int,
        limit: int,
        search: Optional[str],
    ) -> RegistrationListResponse:
        registrations, total = self.reg_repo.list_registrations(
            event_id=event_id, status=status, page=page, limit=limit, search=search
        )
        total_pages = (total + limit - 1) // limit if limit else 1
        pagination = RegistrationListPagination(
            total=total, page=page, limit=limit, total_pages=total_pages
        )
        return RegistrationListResponse(registrations=registrations, pagination=pagination)

    def get_registration_detail(self, registration_id: UUID) -> RegistrationWithFilesResponse:
        registration = self.reg_repo.get_registration_by_id(registration_id)
        if not registration:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=REGISTRATION_NOT_FOUND)
        files = self.files_repo.get_files_by_registration(registration_id)
        return RegistrationWithFilesResponse(**registration.model_dump(), files=files)

    # Analytics removed (moved to analytics subdomain)

