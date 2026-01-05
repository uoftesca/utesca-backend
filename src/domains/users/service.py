"""
User service - Business logic for user management operations.

This module handles business logic for user management.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client, create_client
from supabase_auth.errors import AuthApiError, AuthInvalidCredentialsError

from core.config import get_settings
from core.database import get_schema, get_supabase_client
from domains.auth.models import UserResponse
from .models import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    DeleteUserResponse,
    UpdateUserRequest,
    UserListResponse,
)
from .repository import UserRepository


logger = logging.getLogger(__name__)

# Error message constants
USER_NOT_FOUND = "User not found"


class UserService:
    """Service class for user management operations."""

    def __init__(self):
        self.settings = get_settings()
        self.schema = get_schema()
        self.supabase = get_supabase_client()
        self._admin_client: Optional[Client] = None
        self.repository = UserRepository(self._get_admin_client(), self.schema)

    def _get_admin_client(self) -> Client:
        """
        Get Supabase client with service role key for admin operations.

        This bypasses RLS policies. Access control is enforced at the endpoint level
        by requiring authentication.

        Returns:
            Client: Supabase client with admin privileges
        """
        if self._admin_client is None:
            self._admin_client = create_client(
                self.settings.SUPABASE_URL, self.settings.SUPABASE_SERVICE_ROLE_KEY
            )
        return self._admin_client

    def get_users(
        self,
        department_id: Optional[UUID] = None,
        role: Optional[str] = None,
        year: Optional[int] = None,
        search: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> UserListResponse:
        """
        Get list of users with optional filtering and pagination.

        Args:
            department_id: Filter by department ID
            role: Filter by role
            year: Filter by year
            search: Search query for name/email/role
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            UserListResponse with users and metadata

        Raises:
            HTTPException: If retrieval fails
        """
        try:
            # Calculate offset for pagination
            limit = None
            offset = None

            if page is not None and page_size is not None:
                if page < 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Page must be >= 1",
                    )
                if page_size < 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Page size must be >= 1",
                    )

                limit = page_size
                offset = (page - 1) * page_size

            users, total = self.repository.get_all(
                department_id=department_id,
                role=role,
                year=year,
                search=search,
                limit=limit,
                offset=offset,
            )

            return UserListResponse(
                total=total,
                users=users,
                page=page,
                page_size=page_size,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching users: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch users: {str(e)}",
            ) from e

    def get_user_by_id(self, user_id: UUID) -> UserResponse:
        """
        Get user by ID.

        Args:
            user_id: User UUID

        Returns:
            UserResponse

        Raises:
            HTTPException: If user not found or retrieval fails
        """
        try:
            user = self.repository.get_by_id(user_id)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=USER_NOT_FOUND,
                )

            return user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch user: {str(e)}",
            ) from e

    def _can_manage_user(self, current_user: UserResponse, target_user: UserResponse) -> bool:
        """
        Check if current user has permission to manage target user.

        Args:
            current_user: User performing the action
            target_user: User being managed

        Returns:
            bool: True if current user can manage target user
        """
        # Co-presidents can manage anyone
        if current_user.role == "co_president":
            return True

        # VPs can only manage directors in their department
        if current_user.role == "vp":
            return (
                target_user.role == "director"
                and target_user.department_id == current_user.department_id
                and target_user.department_id is not None
            )

        return False

    def _validate_update_permissions(
        self,
        request: UpdateUserRequest,
        current_user: UserResponse,
        target_user: UserResponse,
    ) -> None:
        """
        Validate that current user has permission to perform the requested update.

        Args:
            request: Update request with fields to change
            current_user: User performing the update
            target_user: User being updated

        Raises:
            HTTPException: If user lacks permission for the requested changes
        """
        # Check basic permission to manage user
        if not self._can_manage_user(current_user, target_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to manage this user",
            )

        # Role changes require co-president
        is_role_change = request.role is not None and request.role != target_user.role
        if is_role_change and current_user.role != "co_president":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only co-presidents can change user roles",
            )

        # Cannot change co-president's role
        if is_role_change and target_user.role == "co_president":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot change the role of a co-president",
            )

        # Department changes require co-president
        is_dept_change = (
            request.department_id is not None and request.department_id != target_user.department_id
        )
        if is_dept_change and current_user.role != "co_president":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only co-presidents can change user departments",
            )

    def _build_update_data(self, request: UpdateUserRequest) -> dict:
        """
        Build update data dictionary from request.

        Args:
            request: Update request with fields to change

        Returns:
            Dictionary of fields to update

        Raises:
            HTTPException: If no fields to update
        """
        update_data = {}
        if request.first_name is not None:
            update_data["first_name"] = request.first_name
        if request.last_name is not None:
            update_data["last_name"] = request.last_name
        if request.display_role is not None:
            update_data["display_role"] = request.display_role
        if request.role is not None:
            update_data["role"] = request.role
        if request.department_id is not None:
            update_data["department_id"] = str(request.department_id)

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )

        return update_data

    def _sync_auth_metadata(self, target_user: UserResponse, request: UpdateUserRequest) -> None:
        """
        Synchronize user metadata to auth.users table.

        This keeps auth.users.user_metadata in sync with the users table.
        Failures are logged but don't cause the operation to fail since
        the users table is the source of truth.

        Args:
            target_user: The user being updated
            request: The update request containing fields to sync
        """
        try:
            metadata_update = {}
            if request.first_name is not None:
                metadata_update["first_name"] = request.first_name
            if request.last_name is not None:
                metadata_update["last_name"] = request.last_name
            if request.display_role is not None:
                metadata_update["display_role"] = request.display_role
            if request.role is not None:
                metadata_update["role"] = request.role
            if request.department_id is not None:
                metadata_update["department_id"] = str(request.department_id)

            if not metadata_update:
                return

            admin_client = self._get_admin_client()

            # Get current metadata first
            auth_user = admin_client.auth.admin.get_user_by_id(str(target_user.user_id))
            current_metadata = auth_user.user.user_metadata or {}

            # Merge updates into existing metadata
            updated_metadata = {**current_metadata, **metadata_update}

            # Update auth user metadata
            admin_client.auth.admin.update_user_by_id(
                uid=str(target_user.user_id),
                attributes={"user_metadata": updated_metadata},
            )
        except Exception as e:
            logger.warning(f"Failed to update auth metadata: {e}")
            # Continue even if metadata update fails (users table is source of truth)

    def update_user(
        self, user_id: UUID, request: UpdateUserRequest, current_user: UserResponse
    ) -> UserResponse:
        """
        Update a user's information.

        Args:
            user_id: ID of user to update
            request: Update request with fields to change
            current_user: User performing the update

        Returns:
            UserResponse: Updated user data

        Raises:
            HTTPException: If update fails or user lacks permission
        """
        try:
            # 1. Fetch target user
            target_user = self.repository.get_by_id(user_id)
            if not target_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=USER_NOT_FOUND,
                )

            # 2. Validate permissions for requested changes
            self._validate_update_permissions(request, current_user, target_user)

            # 3. Build update data
            update_data = self._build_update_data(request)

            # 4. Update users table via repository
            updated_user = self.repository.update(user_id, update_data)

            if not updated_user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update user",
                )

            # 5. Sync auth.users.user_metadata (non-blocking)
            self._sync_auth_metadata(target_user, request)

            return updated_user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update user: {str(e)}",
            ) from e

    def delete_user(self, user_id: UUID, current_user: UserResponse) -> DeleteUserResponse:
        """
        Delete a user from the system.

        Args:
            user_id: ID of user to delete
            current_user: User performing the deletion

        Returns:
            DeleteUserResponse: Confirmation of deletion

        Raises:
            HTTPException: If deletion fails or user lacks permission
        """
        try:
            # 1. Prevent self-deletion
            if user_id == current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You cannot delete yourself",
                )

            # 2. Fetch target user
            target_user = self.repository.get_by_id(user_id)
            if not target_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=USER_NOT_FOUND,
                )

            # 3. Validate permission
            if not self._can_manage_user(current_user, target_user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to delete this user",
                )

            # 4. Delete from auth.users (will cascade to {schema}.users)
            admin_client = self._get_admin_client()
            admin_client.auth.admin.delete_user(str(target_user.user_id))

            return DeleteUserResponse(
                success=True,
                message=f"User {target_user.email} has been deleted",
                deleted_user_id=user_id,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete user: {str(e)}",
            ) from e

    # ============================================================================
    # Password Validation and Change
    # ============================================================================

    def _validate_new_password(self, new_password: str, confirm_password: str) -> None:
        """
        Validate new password meets requirements and matches confirmation.

        Args:
            new_password: New password to validate
            confirm_password: Confirmation password

        Raises:
            HTTPException: If validation fails
        """
        if new_password != confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password and confirmation password do not match",
            )

        if len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters",
            )

    def _verify_current_password(self, email: str, current_password: str) -> None:
        """
        Verify that the current password is correct by attempting sign in.

        Args:
            email: User's email
            current_password: Current password to verify

        Raises:
            HTTPException: If current password is incorrect or verification fails
        """
        try:
            temp_client = create_client(self.settings.SUPABASE_URL, self.settings.SUPABASE_KEY)
            auth_response = temp_client.auth.sign_in_with_password(
                {
                    "email": email,
                    "password": current_password,
                }
            )

            if not (auth_response.session and auth_response.user):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Current password is incorrect",
                )
        except HTTPException:
            raise
        except (AuthInvalidCredentialsError, AuthApiError) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            ) from e
        except Exception as e:
            logger.error(f"Error verifying current password: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to verify current password",
            ) from e

    def _update_password_in_supabase(self, auth_user_id: UUID, new_password: str) -> None:
        """
        Update user password in Supabase Auth.

        Args:
            auth_user_id: Supabase Auth user ID
            new_password: New password to set

        Raises:
            HTTPException: If password update fails
        """
        try:
            admin_client = self._get_admin_client()
            admin_client.auth.admin.update_user_by_id(
                uid=str(auth_user_id),
                attributes={"password": new_password},
            )
        except Exception as e:
            logger.error(f"Error updating password: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password",
            ) from e

    def change_password(
        self, request: ChangePasswordRequest, current_user: UserResponse
    ) -> ChangePasswordResponse:
        """
        Change user password.

        Args:
            request: Password change request
            current_user: Current authenticated user

        Returns:
            ChangePasswordResponse: Success message

        Raises:
            HTTPException: If validation fails or update fails
        """
        try:
            # Validate new password
            self._validate_new_password(request.new_password, request.confirm_password)

            # Verify current password
            self._verify_current_password(current_user.email, request.current_password)

            # Update password
            self._update_password_in_supabase(current_user.user_id, request.new_password)

            return ChangePasswordResponse(message="Password updated successfully")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to change password: {str(e)}",
            ) from e
