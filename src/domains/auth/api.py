"""
Authentication API endpoints.

This module defines the FastAPI router for authentication-related endpoints.
"""

from fastapi import APIRouter, Depends, status
from uuid import UUID

from .models import (
    UserResponse,
    InviteUserRequest,
    InviteUserResponse,
    UpdateProfileRequest,
    CompleteOnboardingRequest,
    SignInRequest,
    SignInResponse,
)
from .service import AuthService
from .dependencies import get_current_user, get_current_admin, get_auth_user_id


# Create router
router = APIRouter()


# ============================================================================
# Authentication Endpoints
# ============================================================================

@router.post(
    "/sign-in",
    response_model=SignInResponse,
    status_code=status.HTTP_200_OK,
    summary="Sign In",
    description="Sign in with email and password",
)
async def sign_in(request: SignInRequest):
    """
    Sign in with email and password.

    **Process:**
    1. Authenticates user with Supabase Auth
    2. Retrieves user profile from users table
    3. Returns access token, refresh token, and user data

    **Returns:**
    - Access token, refresh token, and user profile
    """
    service = AuthService()
    return await service.sign_in(request)


@router.post(
    "/invite",
    response_model=InviteUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite User",
    description="Invite a new user to the portal (admin only)",
)
async def invite_user(
    request: InviteUserRequest,
    current_user: UserResponse = Depends(get_current_admin),
):
    """
    Invite a new user to the portal.

    **Requirements:**
    - Caller must be a co-president (admin)
    - Email must not already be registered

    **Process:**
    1. Sends invitation email via Supabase Auth
    2. Stores first_name, last_name, role, display_role, department, invited_by in user metadata
    3. When user accepts, they set password and optional preferred_name
    4. Database trigger auto-populates users table

    **Returns:**
    - Invitation status and user details
    """
    service = AuthService()
    return await service.invite_user(request, current_user.user_id)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current User",
    description="Get current authenticated user's profile",
)
async def get_current_user_profile(
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Get current authenticated user's profile.

    **Requirements:**
    - User must be authenticated

    **Returns:**
    - User profile data
    """
    return current_user


@router.post(
    "/complete-onboarding",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Complete Onboarding",
    description="Complete onboarding after accepting invite",
)
async def complete_onboarding(
    request: CompleteOnboardingRequest,
    auth_user_id: UUID = Depends(get_auth_user_id),
):
    """
    Complete user onboarding after accepting invite.

    **Process:**
    1. Updates user password in Supabase Auth
    2. Creates user record in users table using metadata from auth.users
    3. Sets optional preferred_name if provided

    **Requirements:**
    - User must have a valid JWT token (from invite acceptance)
    - User must NOT already exist in users table

    **Returns:**
    - Created user profile
    """
    service = AuthService()
    return await service.complete_onboarding(auth_user_id, request)


@router.put(
    "/profile",
    response_model=UserResponse,
    summary="Update Profile",
    description="Update current user's profile",
)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Update current user's profile.

    **Allowed Updates:**
    - preferred_name
    - photo_url
    - announcement_email_preference

    **Requirements:**
    - User must be authenticated
    - Can only update own profile (enforced by RLS)

    **Returns:**
    - Updated user profile
    """
    service = AuthService()
    return await service.update_profile(current_user.id, request)


# ============================================================================
# Health Check / Test Endpoint
# ============================================================================

@router.get(
    "/status",
    summary="Auth Status",
    description="Check authentication service status",
)
async def auth_status():
    """
    Check authentication service status.

    **Returns:**
    - Service status and configuration info
    """
    from core.config import get_settings
    from core.database import get_schema

    settings = get_settings()

    return {
        "status": "ok",
        "service": "authentication",
        "environment": settings.ENVIRONMENT,
        "schema": get_schema(),
        "endpoints": {
            "sign_in": "POST /auth/sign-in",
            "invite": "POST /auth/invite",
            "complete_onboarding": "POST /auth/complete-onboarding",
            "me": "GET /auth/me",
            "update_profile": "PUT /auth/profile",
        },
    }
