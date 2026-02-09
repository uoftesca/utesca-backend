"""
Announcements API endpoints.

This module defines the FastAPI router for announcement-related endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from domains.auth.dependencies import get_current_admin, get_current_user
from domains.auth.models import UserResponse

from .models import (
    AnnouncementCreate,
    AnnouncementListResponse,
    AnnouncementReadResponse,
    AnnouncementResponse,
    AnnouncementUpdate,
    CreateAnnouncementResponse,
    SendAnnouncementEmailRequest,
    SendAnnouncementResponse,
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
    response_model=CreateAnnouncementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Announcement",
    description="Create a new announcement (authenticated users)",
)
async def create_announcement(
    request: AnnouncementCreate,
    current_user: UserResponse = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Create a new announcement in the system.

    **Requirements:**
    - Caller must be authenticated (RLS enforces co-president permission)

    **Request Body:**
    - title: Announcement title (required)
    - content: Announcement content/message (required)
    - priority: "normal" or "urgent" (optional, defaults to "normal")
    - send_email: If true, sends email notification (optional, defaults to false)

    **Returns:**
    - Announcement ID and creation status
    """
    # Create service with user token so RLS policies are enforced
    service = AnnouncementService(user_token=credentials.credentials)
    # Use internal users.id for created_by FK
    # Convert to legacy format for service
    from .models import CreateAnnouncementRequest
    legacy_request = CreateAnnouncementRequest(
        title=request.title,
        content=request.content,
        priority=request.priority,
        send_email=request.send_email,
        expires_at=None,
    )
    return service.create_announcement(legacy_request, current_user.id)


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
     2. Filters based on notification_preferences for normal priority:
         - "all": receives all announcements
         - "urgent_only": only receives urgent announcements
         - "none": never receives announcements
         Urgent priority bypasses preferences and sends to everyone.
    3. Sends emails via Supabase
    4. Optionally creates announcement record if send_email=true

    **Request Body:**
    - title: Email subject line (required)
    - content: Email message body as plain text (required)
    - priority: "normal" or "urgent" (optional, defaults to "normal")

    **Returns:**
    - Delivery stats and status message
    """
    # Use service without token (admin client) since we need to fetch all users
    service = AnnouncementService()
    # Use internal users.id for created_by FK
    return service.send_announcement_email(request, current_user.id)


@router.get(
    "/",
    response_model=AnnouncementListResponse,
    summary="List Announcements",
    description="Get list of announcements (all authenticated users)",
)
async def get_announcements(
    page: int = 1,
    page_size: int = 50,
    current_user: UserResponse = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Get list of announcements with pagination.

    **Requirements:**
    - Caller must be authenticated

    **Query Parameters:**
    - page: Page number (1-indexed, default: 1)
    - page_size: Number of items per page (default: 50)

    **Returns:**
    - List of announcements with metadata
    """
    # Create service with user token so RLS policies are enforced
    service = AnnouncementService(user_token=credentials.credentials)
    return service.get_announcements(page=page, page_size=page_size)


@router.post(
    "/{announcement_id}/read",
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
    # Create service with user token so RLS policies are enforced
    service = AnnouncementService(user_token=credentials.credentials)
    # Use internal users.id for read tracking
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
    # Create service with user token so RLS policies are enforced
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
    - Caller must be co-president OR the creator of the announcement (enforced by RLS)

    **Request Body:**
    - title: New title (optional)
    - content: New content (optional)
    - priority: New priority (optional)

    **Returns:**
    - Updated announcement
    """
    # Create service with user token so RLS policies are enforced
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
    status_code=status.HTTP_200_OK,
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
    - Caller must be co-president OR the creator of the announcement (enforced by RLS)

    **Returns:**
    - Success message
    """
    # Create service with user token so RLS policies are enforced
    service = AnnouncementService(user_token=credentials.credentials)
    return service.delete_announcement(announcement_id, current_user.id)
