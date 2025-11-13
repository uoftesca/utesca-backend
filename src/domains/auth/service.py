"""
Authentication service - Business logic for authentication operations.

This module handles user invitation and profile management.
"""

from fastapi import HTTPException, status
from typing import Optional
from uuid import UUID
from supabase import create_client, Client
from supabase_auth.errors import AuthApiError, AuthInvalidCredentialsError

from core.database import get_supabase_client, get_schema
from core.config import get_settings
from .models import (
    UserResponse,
    InviteUserRequest,
    UpdateProfileRequest,
    InviteUserResponse,
    CompleteOnboardingRequest,
    SignInRequest,
    SignInResponse,
)
from .repository import UserRepository


class AuthService:
    """Service class for authentication operations."""

    def __init__(self):
        self.settings = get_settings()
        self.supabase = get_supabase_client()
        self.schema = get_schema()
        self.repository = UserRepository(self.supabase, self.schema)

    def _get_admin_client(self) -> Client:
        """
        Get Supabase client with service role key for admin operations.

        Returns:
            Client: Supabase client with admin privileges
        """
        return create_client(
            self.settings.SUPABASE_URL,
            self.settings.SUPABASE_SERVICE_ROLE_KEY
        )

    def invite_user(
        self,
        request: InviteUserRequest,
        invited_by_user_id: UUID
    ) -> InviteUserResponse:
        """
        Invite a new user to the portal.

        Args:
            request: Invite user request data
            invited_by_user_id: ID of the user (co-president) sending the invitation

        Returns:
            InviteUserResponse: Response with invitation status

        Raises:
            HTTPException: If invitation fails
        """
        try:
            admin_client = self._get_admin_client()

            # Use BASE_URL from environment configuration
            redirect_to = f"{self.settings.BASE_URL}/accept-invite"

            # Prepare user metadata to be stored in auth.users
            user_metadata = {
                "first_name": request.first_name,
                "last_name": request.last_name,
                "role": request.role,
                "display_role": request.display_role,
                "department_id": str(request.department_id) if request.department_id else None,
                "schema": self.schema,  # Store which schema to use (test/prod)
                "invited_by": str(invited_by_user_id),
            }

            # Invite user via Supabase Admin API
            result = admin_client.auth.admin.invite_user_by_email(
                email=request.email,
                options={
                    "data": user_metadata,
                    "redirect_to": redirect_to,
                }
            )

            if not result or not result.user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to send invitation",
                )

            return InviteUserResponse(
                success=True,
                message=f"Invitation sent to {request.email}",
                email=request.email,
            )

        except HTTPException:
            raise
        except Exception as e:
            print(f"Error inviting user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to invite user: {str(e)}",
            )

    def update_profile(
        self,
        user_id: UUID,
        request: UpdateProfileRequest,
    ) -> UserResponse:
        """
        Update user profile.

        Args:
            user_id: User ID from users table
            request: Update profile request data

        Returns:
            UserResponse: Updated user data

        Raises:
            HTTPException: If update fails
        """
        try:
            # Build update data (only include fields that are provided)
            update_data = {}
            if request.preferred_name is not None:
                update_data["preferred_name"] = request.preferred_name
            if request.photo_url is not None:
                update_data["photo_url"] = request.photo_url
            if request.announcement_email_preference is not None:
                update_data["announcement_email_preference"] = request.announcement_email_preference
            if request.linkedin_url is not None:
                update_data["linkedin_url"] = request.linkedin_url

            if not update_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No fields to update",
                )

            # Update user in database
            result = self.supabase.schema(self.schema).table("users") \
                .update(update_data) \
                .eq("id", str(user_id)) \
                .execute()

            if not result.data or len(result.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )

            return UserResponse(**result.data[0])

        except HTTPException:
            raise
        except Exception as e:
            print(f"Error updating profile: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update profile: {str(e)}",
            )

    def get_user_by_id(self, user_id: UUID) -> UserResponse:
        """
        Get user by ID.

        Args:
            user_id: User ID from users table

        Returns:
            UserResponse: User data

        Raises:
            HTTPException: If user not found
        """
        try:
            user = self.repository.get_by_id(user_id)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )

            return user

        except HTTPException:
            raise
        except Exception as e:
            print(f"Error fetching user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch user: {str(e)}",
            )

    def complete_onboarding(
        self,
        auth_user_id: UUID,
        request: CompleteOnboardingRequest,
    ) -> UserResponse:
        """
        Complete user onboarding after accepting invite.

        This method:
        1. Updates the user's password in Supabase Auth
        2. Creates a user record in the users table using metadata from auth.users
        3. Optionally sets preferred_name if provided

        Args:
            auth_user_id: Supabase Auth user ID (from JWT)
            request: Onboarding request with password and optional preferred_name

        Returns:
            UserResponse: Created user profile

        Raises:
            HTTPException: If onboarding fails
        """
        try:
            admin_client = self._get_admin_client()

            # 1. Update password and preferred_name in Supabase Auth
            print(f"Updating password for user {auth_user_id}")

            # Prepare update attributes
            update_attributes = {"password": request.password}

            # If preferred_name is provided, also update user_metadata
            if request.preferred_name:
                # First, get current user to retrieve existing metadata
                current_user = admin_client.auth.admin.get_user_by_id(str(auth_user_id))
                current_metadata = current_user.user.user_metadata or {}

                # Merge preferred_name into existing metadata
                updated_metadata = {**current_metadata, "preferred_name": request.preferred_name}
                update_attributes["user_metadata"] = updated_metadata

            update_result = admin_client.auth.admin.update_user_by_id(
                uid=str(auth_user_id),
                attributes=update_attributes
            )

            if not update_result or not update_result.user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update password and/or user metadata",
                )

            # 2. Get user metadata from auth.users
            auth_user = update_result.user
            metadata = auth_user.user_metadata or {}

            # Validate required metadata
            required_fields = ["first_name", "last_name", "role", "display_role"]
            missing_fields = [field for field in required_fields if field not in metadata]
            if missing_fields:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required metadata: {', '.join(missing_fields)}",
                )

            # 3. Create user record in users table
            user_data = {
                "user_id": str(auth_user_id),
                "email": auth_user.email,
                "first_name": metadata["first_name"],
                "last_name": metadata["last_name"],
                "role": metadata["role"],
                "display_role": metadata["display_role"],
                "department_id": metadata.get("department_id"),
                "preferred_name": request.preferred_name,
                "invited_by": metadata.get("invited_by"),
                "announcement_email_preference": "all",
            }

            print(f"Creating user record: {user_data}")

            # Use admin client to bypass RLS policies
            result = admin_client.schema(self.schema).table("users") \
                .insert(user_data) \
                .execute()

            if not result.data or len(result.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user profile",
                )

            return UserResponse(**result.data[0])

        except HTTPException:
            raise
        except Exception as e:
            print(f"Error completing onboarding: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to complete onboarding: {str(e)}",
            )

    def sign_in(self, request: SignInRequest) -> SignInResponse:
        """
        Sign in a user with email and password.

        Args:
            request: Sign in request with email and password

        Returns:
            SignInResponse: Access token, refresh token, and user data

        Raises:
            HTTPException: If sign in fails
        """
        try:
            # Sign in with Supabase Auth
            auth_response = self.supabase.auth.sign_in_with_password({
                "email": request.email,
                "password": request.password,
            })

            if not auth_response.session or not auth_response.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password",
                )

            # Get user from users table
            user_id = auth_response.user.id
            user_data = self.repository.get_by_auth_id(UUID(user_id))

            if not user_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User profile not found. Please complete onboarding.",
                )

            return SignInResponse(
                access_token=auth_response.session.access_token,
                token_type="bearer",
                expires_in=auth_response.session.expires_in or 3600,
                refresh_token=auth_response.session.refresh_token or "",
                user=user_data,
            )

        except HTTPException:
            raise
        except (AuthInvalidCredentialsError, AuthApiError) as e:
            # Handle Supabase auth-specific errors
            print(f"Auth error signing in: {e}")

            # Check for invalid credentials error code
            if isinstance(e, AuthInvalidCredentialsError) or \
               (isinstance(e, AuthApiError) and e.code == "invalid_credentials"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password",
                )

            # Other auth errors (rate limiting, user banned, etc.)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=e.message if hasattr(e, 'message') else str(e),
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred during sign in. Please try again.",
            )

