"""
Event domain models.

Pydantic models for event-related data structures.
"""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

# ============================================================================
# Enums (matching database schema)
# ============================================================================

EventStatus = Literal["draft", "pending_approval", "sent_back", "published"]


class RegistrationFormSchema(BaseModel):
    """Schema definition for dynamic registration form."""

    auto_accept: bool = False
    fields: List[dict] = Field(default_factory=list)

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


# ============================================================================
# Request Models
# ============================================================================

class EventCreate(BaseModel):
    """Request to create a new event."""

    slug: Optional[str] = Field(None, min_length=1)
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    date_time: datetime
    location: Optional[str] = Field(None, max_length=255)
    registration_deadline: Optional[datetime] = None
    status: EventStatus = Field(default="draft")
    registration_form_schema: Optional[RegistrationFormSchema] = None
    max_capacity: Optional[int] = Field(None, gt=0)
    image_url: Optional[str] = None
    category: Optional[str] = None
    image_position: Optional[str] = None
    album_link: Optional[str] = None
    registration_link: Optional[str] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )


class EventUpdate(BaseModel):
    """Request to update an event (all fields optional)."""

    slug: Optional[str] = Field(None, min_length=1)
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    date_time: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=255)
    registration_deadline: Optional[datetime] = None
    status: Optional[EventStatus] = None
    registration_form_schema: Optional[RegistrationFormSchema] = None
    max_capacity: Optional[int] = Field(None, gt=0)
    image_url: Optional[str] = None
    category: Optional[str] = None
    image_position: Optional[str] = None
    album_link: Optional[str] = None
    registration_link: Optional[str] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )


# ============================================================================
# Response Models
# ============================================================================

class EventResponse(BaseModel):
    """Event response model with all fields."""

    id: UUID
    slug: str
    title: str
    description: Optional[str] = None
    date_time: datetime
    location: Optional[str] = None
    registration_deadline: Optional[datetime] = None
    status: EventStatus
    created_by: Optional[UUID] = None
    registration_form_schema: Optional[RegistrationFormSchema] = None
    max_capacity: Optional[int] = None
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    category: Optional[str] = None
    image_position: Optional[str] = None
    album_link: Optional[str] = None
    registration_link: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True
    )


class EventListResponse(BaseModel):
    """List of events response."""

    events: List[EventResponse]

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )


# ============================================================================
# Legacy Models (kept for backward compatibility during migration)
# ============================================================================

class Event(BaseModel):
    """Legacy model representing a single event (deprecated)."""
    title: str
    date: str
    description: Optional[str] = ""
    category: Optional[str] = ""
    registrationLink: Optional[str] = ""
    image: Optional[str] = ""
    imagePosition: Optional[str | int] = "center"
    albumLink: Optional[str] = ""


class Store(BaseModel):
    """Legacy model representing the event store collection (deprecated)."""
    events: List[Event] = Field(default_factory=list)
