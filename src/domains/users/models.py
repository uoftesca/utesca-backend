"""
Pydantic models for users domain.

These models define the request/response schemas for user endpoints.
"""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

# Import from auth domain to reuse
from domains.auth.models import UserResponse, UserRole

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

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ============================================================================
# Response Models
# ============================================================================


class UserListResponse(BaseModel):
    """List of users with metadata."""

    total: int
    users: List[UserResponse]
    page: Optional[int] = None
    page_size: Optional[int] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class DeleteUserResponse(BaseModel):
    """Response after deleting a user."""

    success: bool
    message: str
    deleted_user_id: UUID

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
