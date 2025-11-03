"""
Pydantic models for users domain.

These models define the request/response schemas for user endpoints.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID

# Import from auth domain to reuse
from domains.auth.models import UserResponse, UserRole, EmailNotificationPreference


# ============================================================================
# Request Models
# ============================================================================

class UpdateUserRequest(BaseModel):
    """Request to update a user's information (admin operation)."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    display_role: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[UserRole] = Field(None, description="Can only be changed by co-presidents")
    department_id: Optional[UUID] = Field(None, description="Can only be changed by co-presidents")


# ============================================================================
# Response Models
# ============================================================================

class UserListResponse(BaseModel):
    """List of users with metadata."""

    total: int
    users: List[UserResponse]
    page: Optional[int] = None
    page_size: Optional[int] = None


class DeleteUserResponse(BaseModel):
    """Response after deleting a user."""

    success: bool
    message: str
    deleted_user_id: UUID
