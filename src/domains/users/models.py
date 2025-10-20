"""
Pydantic models for users domain.

These models define the request/response schemas for user endpoints.
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID

# Import from auth domain to reuse
from domains.auth.models import UserResponse, UserRole, EmailNotificationPreference


# ============================================================================
# Response Models
# ============================================================================

class UserListResponse(BaseModel):
    """List of users with metadata."""

    total: int
    users: List[UserResponse]
    page: Optional[int] = None
    page_size: Optional[int] = None
