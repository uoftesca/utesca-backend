"""
Pydantic models for announcements domain.

These models define the request/response schemas for announcement endpoints.
"""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

# ============================================================================
# Enums
# ============================================================================

AnnouncementPriority = Literal["normal", "urgent"]


# ============================================================================
# Base Models
# ============================================================================

class AnnouncementBase(BaseModel):
    """Base model for announcements with common fields."""

    title: str = Field(..., min_length=1, max_length=500, description="Announcement title")
    content: str = Field(..., min_length=1, description="Announcement content/message body")
    priority: AnnouncementPriority = Field(
        "normal",
        description="Announcement priority: 'normal' or 'urgent'"
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )


# ============================================================================
# Request Models
# ============================================================================

class AnnouncementCreate(AnnouncementBase):
    """Request to create an announcement (inherits from AnnouncementBase)."""

    send_email: bool = Field(
        False,
        description="If true, sends email notification to all users"
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )


class AnnouncementUpdate(BaseModel):
    """Request to update an announcement (all fields optional)."""

    title: Optional[str] = Field(None, min_length=1, max_length=500, description="Announcement title")
    content: Optional[str] = Field(None, min_length=1, description="Announcement content/message body")
    priority: Optional[AnnouncementPriority] = Field(None, description="Announcement priority")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )


class AnnouncementReadStatusUpdate(BaseModel):
    """Request to mark announcement as read (empty body - action is idempotent)."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )


# Legacy model for backward compatibility with existing service methods
class CreateAnnouncementRequest(BaseModel):
    """Legacy: Request to create an announcement with all fields."""

    title: str = Field(..., min_length=1, max_length=500, description="Announcement title")
    content: Optional[str] = Field(None, description="Announcement content/message body")
    priority: AnnouncementPriority = Field(
        "normal",
        description="Announcement priority: 'normal' or 'urgent'"
    )
    send_email: bool = Field(
        False,
        description="If true, sends email notification to all users"
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="When this announcement expires (optional)"
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )



class SendAnnouncementEmailRequest(BaseModel):
    """Request to send an announcement email to users based on preferences."""

    title: str = Field(..., min_length=1, max_length=255, description="Email subject line")
    content: str = Field(..., min_length=1, description="Email message body (plain text)")
    priority: AnnouncementPriority = Field(
        "normal",
        description="Announcement priority: 'normal' or 'urgent'"
    )
    send_to_all: bool = Field(
        False,
        description="If true, sends to all executives. If false, respects notification_preferences.announcements"
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )


# ============================================================================
# Response Models
# ============================================================================

class AnnouncementEmailStats(BaseModel):
    """Statistics about an announcement email send."""

    total_recipients: int = Field(..., description="Total number of users in the system")
    emails_sent: int = Field(..., description="Number of emails successfully sent")
    emails_skipped: int = Field(..., description="Number of users who skipped based on preferences")
    failed_emails: int = Field(..., description="Number of emails that failed to send")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )


class CreateAnnouncementResponse(BaseModel):
    """Response after creating announcement."""

    success: bool = Field(..., description="Whether the announcement was successfully created")
    message: str = Field(..., description="Status message")
    announcement_id: UUID = Field(..., description="ID of the created announcement")
    created_at: datetime = Field(..., description="When the announcement was created")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )


class SendAnnouncementResponse(BaseModel):
    """Response after sending announcement email."""

    success: bool = Field(..., description="Whether the announcement email was successfully sent")
    message: str = Field(..., description="Status message")
    stats: AnnouncementEmailStats = Field(..., description="Email delivery statistics")
    announcement_id: Optional[UUID] = Field(None, description="ID of the announcement record")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )


class AnnouncementResponse(BaseModel):
    """Response for a single announcement record (includes read status for current user)."""

    id: UUID
    title: str
    content: str
    priority: AnnouncementPriority
    created_by: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_read: bool = Field(
        False,
        description="Whether the current user has marked this announcement as read"
    )

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True
    )


class AnnouncementWithReadCount(BaseModel):
    """Announcement with read count statistics."""

    id: UUID
    title: str
    content: str
    priority: AnnouncementPriority
    created_by: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    total_reads: int = Field(..., description="Total number of users who have read this announcement")
    unread_count: int = Field(..., description="Total number of users who have NOT read this announcement")

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True
    )


class AnnouncementReadResponse(BaseModel):
    """Response for announcement read tracking."""

    id: UUID
    announcement_id: UUID
    user_id: UUID
    read_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True
    )


class AnnouncementListResponse(BaseModel):
    """List of announcements with metadata."""

    total: int
    announcements: List[AnnouncementResponse]
    page: Optional[int] = None
    page_size: Optional[int] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
