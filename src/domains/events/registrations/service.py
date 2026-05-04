"""
Business logic for event registrations.
"""

import io
import json
import logging
import re
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from supabase import Client, create_client

from core.config import get_settings
from core.database import get_schema
from core.email import EmailService
from utils.file_utils import deduplicate_filename, generate_zip_filename
from utils.timezone import format_datetime_toronto

from ..models import EventResponse, RegistrationFormSchema
from ..repository import EventRepository
from .files_repository import RegistrationFilesRepository
from .models import (
    FileMeta,
    FileUploadRequest,
    RegistrationListPagination,
    RegistrationListResponse,
    RegistrationResponse,
    RegistrationStatus,
    RegistrationWithFilesResponse,
)
from .repository import RegistrationsRepository

logger = logging.getLogger(__name__)

REGISTRATION_NOT_FOUND = "Registration not found"
EVENT_NOT_FOUND = "Event not found"
REGISTRATION_NOT_ACCESSIBLE = "Registration not found or not accessible"
NOT_ELIGIBLE_FOR_CONFIRMATION = "Registration is not eligible for confirmation"
EVENT_PASSED = "Cannot confirm attendance - event has already passed"
RSVP_CUTOFF_PASSED = "Cannot change RSVP - cutoff is 24 hours before event"


class RegistrationService:
    """Service layer for handling registration lifecycle."""

    MAX_FILE_SIZE = 2_097_152  # 2MB
    ALLOWED_TYPES = {"application/pdf"}

    def __init__(self):
        settings = get_settings()
        self.schema = get_schema()
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        self.events_repo = EventRepository(self.supabase, self.schema)
        self.reg_repo = RegistrationsRepository(self.supabase, self.schema)
        self.files_repo = RegistrationFilesRepository(self.supabase, self.schema)
        # User repository for querying notification preferences
        from domains.users.repository import UserRepository

        self.user_repo = UserRepository(self.supabase, self.schema)

    # -------------------------------------------------------------------------
    # RSVP link helpers
    # -------------------------------------------------------------------------
    def _add_rsvp_link(self, registration: RegistrationResponse) -> None:
        """
        Add RSVP link to registration if status is accepted.

        Business rule: Only accepted registrations have RSVP links.
        """
        settings = get_settings()
        registration.rsvp_link = (
            f"{settings.BASE_URL_PUBLIC}/rsvp/{registration.id}" if registration.status == "accepted" else None
        )

    def _add_rsvp_links(self, registrations: List[RegistrationResponse]) -> None:
        """Add RSVP links to a list of registrations."""
        for reg in registrations:
            self._add_rsvp_link(reg)

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
                if field_type == "file":
                    validator(field, files, errors)
                else:
                    validator(field, value, errors)  # type: ignore[arg-type]

        return errors

    # -------------------------------------------------------------------------
    # Core operations
    # -------------------------------------------------------------------------
    def _get_event_or_404(self, slug: str):
        event = self.events_repo.get_by_slug(slug)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EVENT_NOT_FOUND,
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

    def _disable_auto_accept_if_capacity_reached(self, event, form_schema: RegistrationFormSchema) -> None:
        """
        When capacity is reached, flip auto_accept off so future submissions are reviewed.
        """
        if not event.max_capacity:
            return
        if not form_schema.auto_accept:
            return

        registration_count = self.reg_repo.count_by_event(event.id)
        if registration_count >= event.max_capacity:
            updated_schema = form_schema.model_copy(update={"auto_accept": False})
            self.events_repo.update_form_schema(event.id, updated_schema)

    def submit_registration(
        self, event_slug: str, form_data: Dict[str, Any], upload_session_id: str
    ) -> RegistrationResponse:
        event = self._get_event_or_404(event_slug)
        self._enforce_deadline(event)

        form_schema_model: RegistrationFormSchema = event.registration_form_schema or RegistrationFormSchema()
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
        attendee_count = self.reg_repo.count_accepted_and_confirmed(event.id)
        if event.max_capacity is not None and attendee_count >= event.max_capacity and auto_accept:
            status_value: RegistrationStatus = "waitlist"

        registration = self.reg_repo.create_registration(
            event_id=event.id,
            form_data=form_data,
            status=status_value,
        )

        # Link files after successful creation
        self.files_repo.link_files_to_registration(
            upload_session_id=upload_session_id,
            registration_id=registration.id,
            event_date=event.date_time,
        )

        # self._disable_auto_accept_if_capacity_reached(event, form_schema_model)

        return registration

    def _extract_name(self, form_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract user's name from form data with fallback logic.

        Tries in order: fullName → firstName + lastName → None
        (Supports legacy snake_case for backward compatibility)

        Args:
            form_data: Form submission data

        Returns:
            User's name or None if no name fields found
        """
        # Try fullName first (new standard)
        if full_name := form_data.get("fullName"):
            return str(full_name).strip()

        # Legacy fallback for snake_case
        if full_name := form_data.get("full_name"):
            return str(full_name).strip()

        # Try firstName + lastName (new standard)
        first = form_data.get("firstName", "")
        last = form_data.get("lastName", "")

        # Legacy fallback for snake_case
        if not first:
            first = form_data.get("first_name", "")
        if not last:
            last = form_data.get("last_name", "")

        first = first.strip()
        last = last.strip()

        if first or last:
            return f"{first} {last}".strip()

        # No name found
        return None

    def send_confirmation_email(self, registration: RegistrationResponse, event) -> None:
        """
        Send confirmation email after successful registration.

        Email sending failures are logged but do not block registration.
        This method is called as a background task.

        Args:
            registration: The created registration
            event: The event object
        """
        try:
            # Extract email from form_data
            email = registration.form_data.get("email")
            if not email:
                logger.warning(
                    f"No email found in form_data for registration {registration.id}. Skipping confirmation email."
                )
                return

            # Extract user's name (with fallback)
            full_name = self._extract_name(registration.form_data)

            # Format event datetime to Toronto timezone
            event_datetime_str = format_datetime_toronto(event.date_time)

            # Get base URL from settings for public RSVP links
            settings = get_settings()
            base_url = settings.BASE_URL_PUBLIC

            # Initialize email service
            email_service = EmailService()

            # Determine if auto-accepted
            auto_accept = registration.status == "accepted"

            waitlist = registration.status == "waitlist"

            # Send appropriate email based on auto_accept
            if auto_accept:
                success = email_service.send_registration_confirmation(
                    to=email,
                    full_name=full_name,
                    event_title=event.title,
                    event_datetime=event_datetime_str,
                    event_location=event.location or "TBA",
                    registration_id=str(registration.id),
                    base_url=base_url,
                )
            elif waitlist:
                success = email_service.send_application_waitlisted(
                    to=email,
                    full_name=full_name,
                    event_title=event.title,
                    event_datetime=event_datetime_str,
                    event_location=event.location or "TBA",
                )
            else:
                success = email_service.send_application_received(
                    to=email,
                    full_name=full_name,
                    event_title=event.title,
                    event_datetime=event_datetime_str,
                    event_location=event.location or "TBA",
                )

            if success:
                logger.info(f"Confirmation email sent successfully for registration {registration.id} to {email}")
            else:
                logger.warning(f"Failed to send confirmation email for registration {registration.id} to {email}")

        except Exception as e:
            # Log but don't raise - email failures should not block registration
            logger.error(
                f"Error sending confirmation email for registration {registration.id}: {str(e)}",
                exc_info=True,
            )

    def send_attendance_confirmed_email(self, registration: RegistrationResponse, event) -> None:
        """
        Send attendance confirmation email after user confirms via RSVP page.

        Email sending failures are logged but do not block the confirmation.
        This method is called as a background task.

        Args:
            registration: The registration record
            event: The event object
        """
        try:
            # Extract email from form_data
            email = registration.form_data.get("email")
            if not email:
                logger.warning(
                    f"No email found in form_data for registration {registration.id}. "
                    "Skipping attendance confirmation email."
                )
                return

            # Extract user's name (with fallback)
            full_name = self._extract_name(registration.form_data)

            # Format event datetime to Toronto timezone
            event_datetime_str = format_datetime_toronto(event.date_time)

            # Get base URL from settings for public RSVP links
            settings = get_settings()
            base_url = settings.BASE_URL_PUBLIC

            # Initialize email service
            email_service = EmailService()

            # Send attendance confirmed email
            success = email_service.send_attendance_confirmed(
                to=email,
                full_name=full_name,
                event_title=event.title,
                event_datetime=event_datetime_str,
                event_location=event.location or "TBA",
                registration_id=str(registration.id),
                base_url=base_url,
            )

            if success:
                logger.info(
                    f"Attendance confirmation email sent successfully for registration {registration.id} to {email}"
                )
            else:
                logger.warning(
                    f"Failed to send attendance confirmation email for registration {registration.id} to {email}"
                )

        except Exception as e:
            # Log but don't raise - email failures should not block confirmation
            logger.error(
                f"Error sending attendance confirmation email for registration {registration.id}: {str(e)}",
                exc_info=True,
            )

    def send_attendance_declined_email(self, registration: RegistrationResponse, event) -> None:
        """
        Send attendance decline confirmation email after user declines via RSVP page.

        Email sending failures are logged but do not block the decline action.
        This method is called as a background task.

        Args:
            registration: The registration record
            event: The event object
        """
        try:
            # Extract email from form_data
            email = registration.form_data.get("email")
            if not email:
                logger.warning(
                    f"No email found in form_data for registration {registration.id}. "
                    "Skipping attendance decline email."
                )
                return

            # Extract user's name (with fallback)
            full_name = self._extract_name(registration.form_data)

            # Format event datetime to Toronto timezone
            event_datetime_str = format_datetime_toronto(event.date_time)

            # Initialize email service
            email_service = EmailService()

            # Send attendance declined email
            success = email_service.send_attendance_declined(
                to=email,
                full_name=full_name,
                event_title=event.title,
                event_datetime=event_datetime_str,
                event_location=event.location or "TBA",
            )

            if success:
                logger.info(f"Attendance decline email sent successfully for registration {registration.id} to {email}")
            else:
                logger.warning(f"Failed to send attendance decline email for registration {registration.id} to {email}")

        except Exception as e:
            # Log but don't raise - email failures should not block decline action
            logger.error(
                f"Error sending attendance decline email for registration {registration.id}: {str(e)}",
                exc_info=True,
            )

    def send_decline_notification_to_subscribed_users(
        self,
        registration: RegistrationResponse,
        event,
        previous_status: str,
    ) -> None:
        """
        Send notification emails to subscribed users when attendee declines confirmed attendance.

        Only sends if previous_status was "confirmed" (not "accepted").
        Queries users with notification_preferences.rsvp_changes = true.

        Email sending failures are logged but do not block the decline action.
        This method is called as a background task.

        Args:
            registration: The registration record (after status update)
            event: The event object
            previous_status: Status before decline ("confirmed" or "accepted")
        """
        try:
            # Only send notifications if declined from confirmed status
            if previous_status != "confirmed":
                logger.info(
                    f"Skipping decline notification for registration {registration.id} - "
                    f"previous status was '{previous_status}', not 'confirmed'"
                )
                return

            # Query users with rsvp_changes notification enabled
            subscribed_users = self.user_repo.get_users_with_notification_enabled("rsvp_changes")

            if not subscribed_users:
                logger.info("No users subscribed to RSVP change notifications")
                return

            # Extract attendee information
            attendee_email = registration.form_data.get("email")
            if not attendee_email:
                logger.warning(
                    f"No email found in form_data for registration {registration.id}. "
                    "Skipping decline notification to subscribed users."
                )
                return

            attendee_name = self._extract_name(registration.form_data)

            # Build recipient list
            recipient_emails = [user.email for user in subscribed_users]

            # Format event datetime
            event_datetime_str = format_datetime_toronto(event.date_time)

            # Initialize email service
            email_service = EmailService()

            # Send notification to all subscribed users
            success = email_service.send_rsvp_decline_notification(
                to_emails=recipient_emails,
                attendee_name=attendee_name,
                attendee_email=attendee_email,
                event_title=event.title,
                event_datetime=event_datetime_str,
                event_location=event.location or "TBA",
                previous_status=previous_status,
            )

            if success:
                logger.info(
                    f"RSVP decline notification sent successfully for registration {registration.id} "
                    f"to {len(recipient_emails)} subscribed user(s)"
                )
            else:
                logger.warning(f"Failed to send RSVP decline notification for registration {registration.id}")

        except Exception as e:
            # Log but don't raise - email failures should not block decline action
            logger.error(
                f"Error sending decline notification to subscribed users for registration {registration.id}: {str(e)}",
                exc_info=True,
            )

    def handle_decline_notifications(
        self,
        registration_id: UUID,
        previous_status: str,
    ) -> None:
        """
        Handle all email notifications for RSVP decline.

        Sends:
        - Confirmation email to decliner
        - Notification to subscribed users (if declined from confirmed status)

        This method encapsulates all notification business logic.
        Called as background task from API layer.

        Args:
            registration_id: ID of the declined registration
            previous_status: Status before decline (for determining notifications)
        """
        import logging

        logger = logging.getLogger(__name__)

        try:
            # Fetch registration and event
            registration = self.reg_repo.get_registration_public(registration_id)
            if not registration:
                logger.warning(f"Registration {registration_id} not found for notification")
                return

            event = self.events_repo.get_by_id(registration.event_id)
            if not event:
                logger.warning(f"Event not found for registration {registration_id}")
                return

            # Send decliner confirmation email
            if registration.form_data.get("email"):
                self.send_attendance_declined_email(registration, event)

            # Send subscriber notifications if declined from confirmed status
            if previous_status == "confirmed":
                self.send_decline_notification_to_subscribed_users(registration, event, previous_status)

        except Exception as e:
            # Log but don't raise - email failures should not block decline action
            logger.error(
                f"Failed to send decline notifications for registration {registration_id}: {e}",
                exc_info=True,
            )

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

    def delete_uploaded_file(self, event_slug: str, file_id: UUID, upload_session_id: str, field_name: str) -> None:
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

    def send_acceptance_email(
        self,
        registration: RegistrationResponse,
        event: EventResponse,
    ) -> None:
        """
        Send acceptance email after VP/Admin accepts application.

        Email sending failures are logged but do not block the acceptance.
        This method is called as a background task.

        Args:
            registration: The registration record (status = accepted)
            event: The event object (includes custom templates if set)
        """
        self._send_status_email(
            registration=registration,
            event=event,
            action_name="acceptance",
            custom_template=event.acceptance_email_template,
            send_fn=EmailService().send_application_acceptance,
            extra_kwargs={
                "registration_id": str(registration.id),
                "base_url": get_settings().BASE_URL_PUBLIC,
            },
        )

    def send_rejection_email(
        self,
        registration: RegistrationResponse,
        event: EventResponse,
    ) -> None:
        self._send_status_email(
            registration=registration,
            event=event,
            action_name="rejection",
            custom_template=event.rejection_email_template,
            send_fn=EmailService().send_application_rejection,
        )

    def send_waitlisted_email(
        self,
        registration: RegistrationResponse,
        event: EventResponse,
    ) -> None:
        self._send_status_email(
            registration=registration,
            event=event,
            action_name="waitlisted",
            custom_template=event.waitlisted_email_template,
            send_fn=EmailService().send_application_waitlisted,
        )

    def _send_status_email(
        self,
        registration: RegistrationResponse,
        event: EventResponse,
        action_name: str,
        custom_template: Any,
        send_fn: Callable[..., bool],
        extra_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            email = registration.form_data.get("email")
            if not email:
                logger.warning(
                    f"No email found in form_data for registration {registration.id}. Skipping {action_name} email."
                )
                return

            full_name = self._extract_name(registration.form_data)
            event_datetime_str = format_datetime_toronto(event.date_time)

            kwargs: Dict[str, Any] = {
                "to": email,
                "full_name": full_name,
                "event_title": event.title,
                "event_datetime": event_datetime_str,
                "event_location": event.location or "TBA",
                "custom_template": custom_template,
            }
            if extra_kwargs:
                kwargs.update(extra_kwargs)

            success = send_fn(**kwargs)

            if success:
                logger.info(
                    f"{action_name.capitalize()} email sent successfully for registration {registration.id} to {email}"
                )
            else:
                logger.warning(f"Failed to send {action_name} email for registration {registration.id} to {email}")

        except Exception as e:
            logger.error(
                f"Error sending {action_name} email for registration {registration.id}: {str(e)}",
                exc_info=True,
            )

    def accept_application(self, registration_id: UUID, reviewer_id: UUID) -> RegistrationResponse:
        registration = self.reg_repo.get_registration_by_id(registration_id)
        if not registration:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=REGISTRATION_NOT_FOUND)
        if registration.status != "submitted" and registration.status != "waitlist":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only submitted or waitlisted registrations can be accepted",
            )

        updated = self.reg_repo.update_status(
            registration_id=registration_id,
            status="accepted",
            reviewer_id=reviewer_id,
            reviewed_at=datetime.now(timezone.utc),
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update status")

        # Add RSVP link to accepted registration
        self._add_rsvp_link(updated)

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

        # Add RSVP link (will be null for rejected status)
        self._add_rsvp_link(updated)

        return updated

    def waitlist_application(self, registration_id: UUID, reviewer_id: UUID) -> RegistrationResponse:
        registration = self.reg_repo.get_registration_by_id(registration_id)
        if not registration:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=REGISTRATION_NOT_FOUND)
        if registration.status != "submitted":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only submitted registrations can be waitlisted",
            )
        updated = self.reg_repo.update_status(
            registration_id=registration_id,
            status="waitlist",
            reviewer_id=reviewer_id,
            reviewed_at=datetime.now(timezone.utc),
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update status")

        # Add RSVP link (will be null for waitlisted status)
        self._add_rsvp_link(updated)

        return updated

    def _has_event_passed(self, event_date: datetime) -> bool:
        """
        Check if the event date has passed.

        Args:
            event_date: The event's date_time

        Returns:
            True if event has passed, False otherwise
        """
        now = datetime.now(timezone.utc)
        event_dt = event_date if event_date.tzinfo else event_date.replace(tzinfo=timezone.utc)
        return now > event_dt

    def _is_within_rsvp_cutoff(self, event_date: datetime) -> bool:
        """
        Check if current time is within the 24-hour RSVP cutoff period.

        Returns True if we are within 24 hours of the event (cutoff has passed).
        Returns False if we are more than 24 hours before the event (changes allowed).

        Args:
            event_date: The event's date_time

        Returns:
            True if within 24-hour cutoff (changes NOT allowed), False otherwise
        """
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        event_dt = event_date if event_date.tzinfo else event_date.replace(tzinfo=timezone.utc)
        cutoff_time = event_dt - timedelta(hours=24)
        return now >= cutoff_time

    def rsvp_details(self, registration_id: UUID) -> tuple:
        """
        Get RSVP details for public access.

        Returns registration and event details with metadata about allowed actions.
        Only accessible if status is in ['accepted', 'confirmed', 'not_attending'].

        Args:
            registration_id: The registration ID

        Returns:
            Tuple of (registration, event, metadata_dict)

        Raises:
            HTTPException: If registration not found or not accessible
        """
        registration = self.reg_repo.get_registration_public(registration_id)
        if not registration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=REGISTRATION_NOT_ACCESSIBLE,
            )

        event = self.events_repo.get_by_id(UUID(str(registration.event_id)))
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EVENT_NOT_FOUND,
            )

        # Calculate metadata for UI
        event_has_passed = self._has_event_passed(event.date_time)
        within_rsvp_cutoff = self._is_within_rsvp_cutoff(event.date_time)
        current_status = registration.status

        # Terminal statuses that cannot be changed
        is_final = current_status in ("not_attending", "rejected")

        # Can confirm if accepted and event hasn't passed and not within cutoff
        can_confirm = current_status == "accepted" and not event_has_passed and not within_rsvp_cutoff and not is_final

        # Can decline if (accepted or confirmed) and event hasn't passed and not within cutoff
        can_decline = (
            current_status in ("accepted", "confirmed")
            and not event_has_passed
            and not within_rsvp_cutoff
            and not is_final
        )

        metadata = {
            "current_status": current_status,
            "can_confirm": can_confirm,
            "can_decline": can_decline,
            "is_final": is_final,
            "event_has_passed": event_has_passed,
            "within_rsvp_cutoff": within_rsvp_cutoff,
        }

        return registration, event, metadata

    def rsvp_confirm(self, registration_id: UUID) -> RegistrationResponse:
        """
        Confirm attendance.

        Validates that:
        - Registration exists and is accessible
        - Current status is 'accepted'
        - Event has not passed

        Args:
            registration_id: The registration ID

        Returns:
            Updated registration

        Raises:
            HTTPException: If validation fails
        """
        registration = self.reg_repo.get_registration_public(registration_id)
        if not registration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=REGISTRATION_NOT_ACCESSIBLE,
            )

        # Get event to check if it has passed
        event = self.events_repo.get_by_id(UUID(str(registration.event_id)))
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EVENT_NOT_FOUND,
            )

        # Check if event has passed
        if self._has_event_passed(event.date_time):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=EVENT_PASSED,
            )

        # Check if within 24-hour RSVP cutoff
        if self._is_within_rsvp_cutoff(event.date_time):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=RSVP_CUTOFF_PASSED,
            )

        # Allow idempotent confirmation
        if registration.status == "confirmed":
            return registration

        # Only accept 'accepted' status for confirmation
        if registration.status != "accepted":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=NOT_ELIGIBLE_FOR_CONFIRMATION,
            )

        updated = self.reg_repo.confirm_registration(registration_id, confirmed_at=datetime.now(timezone.utc))
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to confirm attendance",
            )

        return updated

    def rsvp_decline(self, registration_id: UUID) -> Tuple[RegistrationResponse, str, EventResponse]:
        """
        Decline attendance (set status to not_attending).

        This is a TERMINAL operation - cannot be reversed.
        Validates that:
        - Registration exists and is accessible
        - Current status is 'accepted' or 'confirmed'
        - Event has not passed

        Args:
            registration_id: The registration ID

        Returns:
            Tuple of (updated_registration, previous_status, event)

        Raises:
            HTTPException: If validation fails
        """
        registration = self.reg_repo.get_registration_public(registration_id)
        if not registration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=REGISTRATION_NOT_ACCESSIBLE,
            )

        # Capture previous status before any changes
        previous_status = registration.status

        # Get event to check if it has passed
        event = self.events_repo.get_by_id(UUID(str(registration.event_id)))
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EVENT_NOT_FOUND,
            )

        # Check if event has passed
        if self._has_event_passed(event.date_time):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot decline attendance - event has already passed",
            )

        # Check if within 24-hour RSVP cutoff
        if self._is_within_rsvp_cutoff(event.date_time):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=RSVP_CUTOFF_PASSED,
            )

        # Allow idempotent decline
        if registration.status == "not_attending":
            return registration, previous_status, event

        # Only allow decline from 'accepted' or 'confirmed'
        if registration.status not in ("accepted", "confirmed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration is not eligible for declining",
            )

        updated = self.reg_repo.set_not_attending(registration_id, declined_at=datetime.now(timezone.utc))
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to decline attendance",
            )

        return updated, previous_status, event

    def list_registrations(
        self,
        event_id: UUID,
        status: Optional[str],
        page: int,
        limit: int,
        search: Optional[str],
    ) -> RegistrationListResponse:
        statuses = [status] if status else None
        registrations, total = self.reg_repo.list_registrations(
            event_id=event_id, statuses=statuses, page=page, limit=limit, search=search
        )

        # Add RSVP links to all registrations
        self._add_rsvp_links(registrations)

        total_pages = (total + limit - 1) // limit if limit else 1
        pagination = RegistrationListPagination(total=total, page=page, limit=limit, total_pages=total_pages)
        return RegistrationListResponse(registrations=registrations, pagination=pagination)

    @staticmethod
    def _camel_to_title(name: str) -> str:
        segments = name.split(".")
        titled = []
        for segment in segments:
            spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", segment)
            titled.append(spaced.replace("_", " ").title())
        return ".".join(titled)

    @staticmethod
    def _flatten_form_data(form_data: Dict[str, Any], prefix: str = "") -> Dict[str, str]:
        result: Dict[str, str] = {}
        for key, value in form_data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if value is None:
                result[full_key] = ""
            elif isinstance(value, dict):
                result.update(RegistrationService._flatten_form_data(value, full_key))
            elif isinstance(value, list):
                if all(isinstance(item, str) for item in value):
                    result[full_key] = ", ".join(value)
                else:
                    result[full_key] = json.dumps(value)
            else:
                result[full_key] = str(value)
        return result

    def _build_column_order(
        self,
        schema_fields: List[dict],
        all_form_keys: List[str],
        file_field_names: set,
    ) -> List[Tuple[str, str]]:
        """
        Derive the ordered list of (column_header, source) pairs for the export.

        Source is one of: "form:<key>", "file:<field_name>".
        Columns follow registration_form_schema field order. File fields from the
        schema emit their File URL column in place. Any form keys present in the
        data but absent from the schema are appended at the end, followed by any
        file fields not in the schema.
        """
        columns: List[Tuple[str, str]] = []
        seen_form_keys: set = set()
        seen_file_fields: set = set()

        for field in schema_fields:
            field_id = field.get("id", "")
            field_type = field.get("type", "")

            if field_type == "file":
                if field_id in file_field_names:
                    columns.append((f"{self._camel_to_title(field_id)} File URL", f"file:{field_id}"))
                    seen_file_fields.add(field_id)
            else:
                # Emit any flattened sub-keys that start with this field_id
                matched = [k for k in all_form_keys if k == field_id or k.startswith(f"{field_id}.")]
                for key in matched:
                    columns.append((self._camel_to_title(key), f"form:{key}"))
                    seen_form_keys.add(key)

        # Append form keys not covered by the schema (preserving first-seen order)
        for key in all_form_keys:
            if key not in seen_form_keys:
                columns.append((self._camel_to_title(key), f"form:{key}"))

        # Append file fields not covered by the schema (sorted)
        for field_name in sorted(file_field_names):
            if field_name not in seen_file_fields:
                columns.append((f"{self._camel_to_title(field_name)} File URL", f"file:{field_name}"))

        return columns

    def export_registrations(self, event_id: UUID, statuses: Optional[List[str]]) -> Tuple[str, List[Dict[str, str]]]:
        event = self.events_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=EVENT_NOT_FOUND)
        slug = event.slug or str(event_id)

        registrations, _ = self.reg_repo.list_registrations(
            event_id=event_id, statuses=statuses, page=1, limit=10_000, search=None
        )
        if not registrations:
            return slug, []

        all_files = self.files_repo.get_files_by_registration_ids([reg.id for reg in registrations])

        files_by_reg: Dict[UUID, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        file_field_names: set = set()
        for f in all_files:
            if f.registration_id is None:
                continue
            files_by_reg[f.registration_id][f.field_name].append(f.file_url)
            file_field_names.add(f.field_name)

        # First pass: flatten form_data and collect all keys in first-seen order
        flattened: List[Dict[str, str]] = []
        all_form_keys: List[str] = []
        seen_keys: set = set()
        for reg in registrations:
            flat = self._flatten_form_data(reg.form_data or {})
            flattened.append(flat)
            for key in flat:
                if key not in seen_keys:
                    all_form_keys.append(key)
                    seen_keys.add(key)

        # Derive column order from the registration form schema
        schema_fields = event.registration_form_schema.fields if event.registration_form_schema else []
        columns = self._build_column_order(schema_fields, all_form_keys, file_field_names)

        # Second pass: build rows
        rows: List[Dict[str, str]] = []
        for reg, flat in zip(registrations, flattened, strict=True):
            row: Dict[str, str] = {
                "Registration ID": str(reg.id),
                "Status": reg.status,
                "Submitted At": str(reg.submitted_at) if reg.submitted_at else "",
                "Reviewed By": str(reg.reviewed_by) if reg.reviewed_by else "",
                "Reviewed At": str(reg.reviewed_at) if reg.reviewed_at else "",
                "Confirmed At": str(reg.confirmed_at) if reg.confirmed_at else "",
                "Checked In": str(reg.checked_in),
                "Checked In At": str(reg.checked_in_at) if reg.checked_in_at else "",
            }

            reg_files = files_by_reg.get(reg.id, {})
            for header, source in columns:
                kind, key = source.split(":", 1)
                if kind == "form":
                    row[header] = flat.get(key, "")
                else:  # file
                    urls = reg_files.get(key, [])
                    row[header] = ", ".join(urls) if urls else ""

            rows.append(row)

        return slug, rows

    # -------------------------------------------------------------------------
    # ZIP bulk file download
    # -------------------------------------------------------------------------
    def download_files_as_zip(self, event_id: UUID) -> Tuple[str, bytes, int]:
        """Download all files from accepted/confirmed registrations as a ZIP archive.

        Returns:
            Tuple of (event_slug, zip_bytes, error_count) where error_count is the
            number of individual file downloads that failed.

        Raises:
            HTTPException: 404 if event not found or no files made it into the archive.
        """
        event = self.events_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=EVENT_NOT_FOUND)

        slug = event.slug or str(event_id)

        registrations, _ = self.reg_repo.list_registrations(
            event_id=event_id, statuses=["accepted", "confirmed"], page=1, limit=10_000, search=None
        )
        if not registrations:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No accepted or confirmed registrations found",
            )

        all_files = self.files_repo.get_files_by_registration_ids([reg.id for reg in registrations])

        # Filter out deleted files and orphans (no registration_id) in-memory
        active_files = [f for f in all_files if not f.deleted and f.registration_id is not None]
        if not active_files:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No downloadable files found")

        # Build a map from registration_id -> form_data for filename generation
        form_data_by_reg: Dict[UUID, Dict[str, Any]] = {reg.id: reg.form_data or {} for reg in registrations}

        # Download each file sequentially, track failures
        file_entries: List[Tuple[str, bytes]] = []
        used_names: set = set()
        error_count = 0

        for file_meta in active_files:
            content = self._download_file_bytes(file_meta.file_url)
            if content is None:
                error_count += 1
                continue

            assert file_meta.registration_id is not None  # Guaranteed by active_files filter  # nosec B101
            form_data = form_data_by_reg.get(file_meta.registration_id, {})
            zip_name = generate_zip_filename(
                field_name=file_meta.field_name,
                form_data=form_data,
                original_filename=file_meta.file_name,
                registration_id=file_meta.registration_id,
            )
            zip_name = deduplicate_filename(zip_name, used_names)
            used_names.add(zip_name)
            file_entries.append((zip_name, content))

        if not file_entries:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="All file downloads failed")

        zip_bytes = self._build_zip_archive(file_entries)
        return slug, zip_bytes, error_count

    def _download_file_bytes(self, url: str) -> Optional[bytes]:
        """Download a single file's raw bytes via HTTP GET.

        Returns None on any network or HTTP error (logged).
        """
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.content
        except Exception as exc:
            logger.warning("Failed to download file from %s: %s", url, exc)
            return None

    @staticmethod
    def _build_zip_archive(file_entries: List[Tuple[str, bytes]]) -> bytes:
        """Write a ZIP archive in memory from pre-downloaded file entries.

        Args:
            file_entries: List of (zip_filename, content_bytes) pairs.

        Returns:
            Complete ZIP archive as bytes.
        """
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name, data in file_entries:
                zf.writestr(name, data)
        return buffer.getvalue()

    def get_registration_detail(self, registration_id: UUID) -> RegistrationWithFilesResponse:
        registration = self.reg_repo.get_registration_by_id(registration_id)
        if not registration:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=REGISTRATION_NOT_FOUND)

        # Add RSVP link to registration
        self._add_rsvp_link(registration)

        files = self.files_repo.get_files_by_registration(registration_id)
        return RegistrationWithFilesResponse(**registration.model_dump(), files=files)

    # Analytics removed (moved to analytics subdomain)
