"""
Pydantic models for authentication domain.

These models define the request/response schemas for authentication endpoints.
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID


# ============================================================================
# Enums (matching database schema)
# ============================================================================

UserRole = Literal["co_president", "vp", "director"]
EmailNotificationPreference = Literal["all", "urgent_only", "none"]


# ============================================================================
# Request Models
# ============================================================================

class InviteUserRequest(BaseModel):
    """Request to invite a new user."""

    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole
    display_role: str = Field(..., min_length=1, max_length=255, description="e.g., 'VP of Events', 'Marketing Director'")
    department_id: Optional[UUID] = None


class UpdateProfileRequest(BaseModel):
    """Request to update user profile."""

    preferred_name: Optional[str] = None
    photo_url: Optional[str] = None
    announcement_email_preference: Optional[EmailNotificationPreference] = None


class CompleteOnboardingRequest(BaseModel):
    """Request to complete onboarding after accepting invite."""

    password: str = Field(..., min_length=8, description="User's chosen password")
    preferred_name: Optional[str] = Field(None, max_length=255, description="Optional preferred name")


class SignInRequest(BaseModel):
    """Request to sign in."""

    email: EmailStr
    password: str = Field(..., min_length=8, description="User's password")


# ============================================================================
# Response Models
# ============================================================================

class UserResponse(BaseModel):
    """User profile response."""

    id: UUID
    user_id: UUID
    email: str
    first_name: str
    last_name: str
    role: UserRole
    display_role: str
    department_id: Optional[UUID] = None
    preferred_name: Optional[str] = None
    photo_url: Optional[str] = None
    invited_by: Optional[UUID] = None
    announcement_email_preference: EmailNotificationPreference
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InviteUserResponse(BaseModel):
    """Response after inviting a user."""

    success: bool
    message: str
    email: str


class SignInResponse(BaseModel):
    """Response after signing in."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str
    user: UserResponse
