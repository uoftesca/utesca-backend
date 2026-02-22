"""
Announcements API endpoints.

This module defines the FastAPI router for announcement-related endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from domains.auth.dependencies import get_current_user
from domains.auth.models import UserResponse

from .models import (
    AnnouncementCreate,
    AnnouncementListResponse,
    AnnouncementReadResponse,
    AnnouncementResponse,
    AnnouncementUpdate,
)
from .service import AnnouncementService

# Create router
router = APIRouter()

# Security scheme for extracting JWT token
security = HTTPBearer()


# ============================================================================
# Announcement Endpoints
# ============================================================================


@router.post(
    "/",
    response_model=AnnouncementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Announcement",
    description="Create a new announcement (co-president or VP only)",
)
async def create_announcement(
    request: AnnouncementCreate,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Create a new announcement in the system.

    **Requirements:**
    - Caller must be a co-president or VP

    **Request Body:**
    - title: Announcement title (required)
    - content: Announcement content/message (required)
    - priority: "normal" or "urgent" (optional, defaults to "normal")
    - send_email: If true, sends email notification (optional, defaults to false)

    **Returns:**
    - Created announcement
    """
    service = AnnouncementService(user_token=credentials.credentials)
    return service.create_announcement(request, current_user.id, background_tasks)


@router.get(
    "/",
    response_model=AnnouncementListResponse,
    summary="List Announcements",
    description="Get list of announcements with read statistics (all authenticated users)",
)
async def get_announcements(
    page: int = 1,
    page_size: int = 50,
    current_user: UserResponse = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Get list of announcements with pagination, read counts, and per-user read status.

    **Requirements:**
    - Caller must be authenticated

    **Query Parameters:**
    - page: Page number (1-indexed, default: 1)
    - page_size: Number of items per page (default: 50)

    **Returns:**
    - List of announcements with total_reads, unread_count, and is_read per item
    """
    service = AnnouncementService(user_token=credentials.credentials)
    return service.get_announcements(user_id=current_user.id, page=page, page_size=page_size)


@router.post(
    "/{announcement_id}/mark-read",
    response_model=AnnouncementReadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Mark Announcement as Read",
    description="Mark an announcement as read by the current user (idempotent)",
)
async def mark_announcement_as_read(
    announcement_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Mark an announcement as read.

    **Requirements:**
    - User must be authenticated

    **Behavior:**
    - Idempotent: If already read, returns existing read record (no error)

    **Returns:**
    - Read record with timestamp
    """
    service = AnnouncementService(user_token=credentials.credentials)
    return service.mark_as_read(announcement_id, current_user.id)


@router.get(
    "/{announcement_id}",
    response_model=AnnouncementResponse,
    summary="Get Single Announcement",
    description="Get a single announcement with read status",
)
async def get_announcement(
    announcement_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Get a single announcement by ID.

    **Requirements:**
    - User must be authenticated

    **Returns:**
    - Announcement with is_read field indicating if current user has read it
    """
    service = AnnouncementService(user_token=credentials.credentials)
    return service.get_announcement(announcement_id, current_user.id)


@router.put(
    "/{announcement_id}",
    response_model=AnnouncementResponse,
    summary="Update Announcement",
    description="Update an announcement (co-president or creator only)",
)
async def update_announcement(
    announcement_id: UUID,
    request: AnnouncementUpdate,
    current_user: UserResponse = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Update an announcement.

    **Requirements:**
    - Caller must be co-president OR the creator of the announcement

    **Request Body:**
    - title: New title (optional)
    - content: New content (optional)
    - priority: New priority (optional)

    **Returns:**
    - Updated announcement
    """
    service = AnnouncementService(user_token=credentials.credentials)
    return service.update_announcement(
        announcement_id=announcement_id,
        title=request.title,
        content=request.content,
        priority=request.priority,
        current_user_id=current_user.id,
    )


@router.delete(
    "/{announcement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Announcement",
    description="Delete an announcement (co-president or creator only)",
)
async def delete_announcement(
    announcement_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Delete an announcement.

    **Requirements:**
    - Caller must be co-president OR the creator of the announcement
    """
    service = AnnouncementService(user_token=credentials.credentials)
    service.delete_announcement(announcement_id, current_user.id)
