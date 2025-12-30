"""
Pydantic models for event registrations and related payloads.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

RegistrationStatus = Literal["submitted", "accepted", "rejected", "confirmed"]


class FileMeta(BaseModel):
    """Metadata for a registration file upload."""

    id: UUID
    registration_id: Optional[UUID] = None
    event_id: UUID
    field_name: str
    file_url: str
    file_name: str
    file_size: int
    mime_type: str
    upload_session_id: str
    uploaded_at: datetime
    scheduled_deletion_date: Optional[date] = None
    deleted: bool
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )


class RegistrationBase(BaseModel):
    """Base registration representation."""

    id: UUID
    event_id: UUID
    form_data: Dict[str, Any]
    status: RegistrationStatus
    submitted_at: datetime
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    rsvp_token: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    checked_in: bool
    checked_in_at: Optional[datetime] = None
    checked_in_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )


class RegistrationCreateRequest(BaseModel):
    """Payload for public registration submission."""

    form_data: Dict[str, Any]
    upload_session_id: str

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class RegistrationResponse(RegistrationBase):
    """Registration response without file details."""

    pass


class RegistrationWithFilesResponse(RegistrationBase):
    """Registration response including uploaded files."""

    files: List[FileMeta] = Field(default_factory=list)


class RegistrationStatusUpdate(BaseModel):
    """Portal status update request."""

    status: Literal["accepted", "rejected"]

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class RegistrationListPagination(BaseModel):
    """Pagination metadata."""

    total: int
    page: int
    limit: int
    total_pages: int

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class RegistrationListResponse(BaseModel):
    """List response with pagination."""

    registrations: List[RegistrationResponse]
    pagination: RegistrationListPagination

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class RegistrationTimelineEntry(BaseModel):
    """Timeline aggregation entry."""

    date: date
    count: int

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class RegistrationStatusBreakdown(BaseModel):
    """Breakdown of registration statuses."""

    submitted: int
    accepted: int
    rejected: int
    confirmed: int
    checked_in: int

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class RegistrationAnalyticsResponse(BaseModel):
    """Analytics response for an event."""

    total_registrations: int
    by_status: RegistrationStatusBreakdown
    approval_rate: float
    attendance_rate: float
    registration_timeline: List[RegistrationTimelineEntry]

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class FileUploadRequest(BaseModel):
    """Payload for Uploadthing callback endpoint."""

    upload_session_id: str
    field_name: str
    file_url: str
    file_name: str
    file_size: int
    mime_type: str
    event_id: UUID

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

class FileUploadResponse(BaseModel):
    """Response after uploading a file."""

    success: bool
    file_id: UUID

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class FileDeleteRequest(BaseModel):
    """Payload for deleting a pre-submission upload."""

    upload_session_id: str
    field_name: str

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class FileDeleteResponse(BaseModel):
    """Response after deleting a file."""

    success: bool

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class RsvpDetailsResponse(BaseModel):
    """Response for viewing RSVP details."""

    event: dict
    registration: dict
    already_confirmed: bool

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class RsvpConfirmResponse(BaseModel):
    """Response after confirming RSVP."""

    success: bool
    message: str
    event: dict

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

