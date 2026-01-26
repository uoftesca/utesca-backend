"""
Announcements API endpoints.

This module defines the FastAPI router for announcement-related endpoints.
"""

from fastapi import APIRouter, Depends, status
from uuid import UUID

from .models import (
    CreateAnnouncementRequest,
    CreateAnnouncementResponse,
    SendAnnouncementEmailRequest,
    SendAnnouncementResponse,
    AnnouncementListResponse,
    AnnouncementReadResponse,
)
from .service import AnnouncementService
from domains.auth.dependencies import get_current_admin, get_current_user
from domains.auth.models import UserResponse


# Create router
router = APIRouter()


# ============================================================================
# Announcement Endpoints
# ============================================================================

@router.post(
    "/",
    response_model=CreateAnnouncementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Announcement",
    description="Create a new announcement (admin only)",
)
async def create_announcement(
    request: CreateAnnouncementRequest,
    current_user: UserResponse = Depends(get_current_admin),
):
    """
    Create a new announcement in the system.

    **Requirements:**
    - Caller must be a co-president (admin)

    **Request Body:**
    - title: Announcement title (required)
    - content: Announcement content/message (optional)
    - priority: "normal" or "urgent" (optional, defaults to "normal")
    - send_email: If true, sends email notification (optional, defaults to false)
    - expires_at: When the announcement expires (optional)

    **Returns:**
    - Announcement ID and creation status
    """
    service = AnnouncementService()
    # Use internal users.id for created_by FK
    return service.create_announcement(request, current_user.id)


@router.post(
    "/send-email",
    response_model=SendAnnouncementResponse,
    status_code=status.HTTP_200_OK,
    summary="Send Announcement Email",
    description="Send an announcement email to all users (admin only)",
)
async def send_announcement_email(
    request: SendAnnouncementEmailRequest,
    current_user: UserResponse = Depends(get_current_admin),
):
    """
    Send an announcement email to all users.

    **Requirements:**
    - Caller must be a co-president (admin)

    **Process:**
    1. Fetches all users from the system
    2. Filters based on announcement_email_preference if send_to_all=False:
       - "all": receives all announcements
       - "urgent_only": only receives urgent announcements
       - "none": never receives announcements
    3. Sends emails via Supabase
    4. Optionally creates announcement record if send_email=true

    **Request Body:**
    - title: Email subject line (required)
    - content: Email message body as plain text (required)
    - priority: "normal" or "urgent" (optional, defaults to "normal")
    - send_to_all: If true, sends to all users ignoring preferences (optional, defaults to true)

    **Returns:**
    - Delivery stats and status message
    """
    service = AnnouncementService()
    # Use internal users.id for created_by FK
    return service.send_announcement_email(request, current_user.id)


@router.get(
    "/",
    response_model=AnnouncementListResponse,
    summary="Get Announcements",
    description="Get list of announcements",
)
async def get_announcements(
    page: int = 1,
    page_size: int = 50,
    current_user: UserResponse = Depends(get_current_admin),
):
    """
    Get list of announcements with pagination.

    **Requirements:**
    - Caller must be a co-president (admin)

    **Query Parameters:**
    - page: Page number (1-indexed, default: 1)
    - page_size: Number of items per page (default: 50)

    **Returns:**
    - List of announcements with metadata
    """
    service = AnnouncementService()
    return service.get_announcements(page=page, page_size=page_size)


@router.post(
    "/{announcement_id}/read",
    response_model=AnnouncementReadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Mark Announcement as Read",
    description="Mark an announcement as read by the current user",
)
async def mark_announcement_as_read(
    announcement_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Mark an announcement as read.

    **Requirements:**
    - User must be authenticated

    **Returns:**
    - Read record with timestamp
    """
    service = AnnouncementService()
    # Use internal users.id for read tracking
    return service.mark_as_read(announcement_id, current_user.id)
