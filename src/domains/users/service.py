"""
User service - Business logic for user management operations.

This module handles business logic for user management.
"""

from fastapi import HTTPException, status
from typing import Optional
from uuid import UUID
from supabase import create_client, Client

from core.database import get_supabase_client, get_schema
from core.config import get_settings
from domains.auth.models import UserResponse
from .models import UserListResponse, UpdateUserRequest, DeleteUserResponse
from .repository import UserRepository


class UserService:
    """Service class for user management operations."""

    def __init__(self):
        self.settings = get_settings()
        self.schema = get_schema()
        # Use admin client to bypass RLS (endpoints are protected by authentication)
        self.supabase = self._get_admin_client()
        self.repository = UserRepository(self.supabase, self.schema)

    def _get_admin_client(self) -> Client:
        """
        Get Supabase client with service role key for admin operations.

        Returns:
            Client: Supabase client with admin privileges
        """
        return create_client(
            self.settings.SUPABASE_URL, self.settings.SUPABASE_SERVICE_ROLE_KEY
        )

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
            print(f"Error fetching users: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch users: {str(e)}",
            )

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

    def _can_manage_user(
        self, current_user: UserResponse, target_user: UserResponse
    ) -> bool:
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
                    detail="User not found",
                )

            # 2. Validate permission
            if not self._can_manage_user(current_user, target_user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to manage this user",
                )

            # 3. Validate role change (only co-presidents)
            if request.role is not None and request.role != target_user.role:
                if current_user.role != "co_president":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Only co-presidents can change user roles",
                    )

            # 4. Validate department change (only co-presidents)
            if (
                request.department_id is not None
                and request.department_id != target_user.department_id
            ):
                if current_user.role != "co_president":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Only co-presidents can change user departments",
                    )

            # 5. Build update data (only include fields that are provided)
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

            # 6. Update users table
            result = (
                self.supabase.schema(self.schema)
                .table("users")
                .update(update_data)
                .eq("id", str(user_id))
                .execute()
            )

            if not result.data or len(result.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update user",
                )

            # 7. Update auth.users.user_metadata to keep synchronized
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

                if metadata_update:
                    # Get current metadata first
                    auth_user = self.supabase.auth.admin.get_user_by_id(
                        str(target_user.user_id)
                    )
                    current_metadata = auth_user.user.user_metadata or {}

                    # Merge updates into existing metadata
                    updated_metadata = {**current_metadata, **metadata_update}

                    # Update auth user metadata
                    self.supabase.auth.admin.update_user_by_id(
                        uid=str(target_user.user_id),
                        attributes={"user_metadata": updated_metadata},
                    )
            except Exception as e:
                print(f"Warning: Failed to update auth metadata: {e}")
                # Continue even if metadata update fails (users table is source of truth)

            return UserResponse(**result.data[0])

        except HTTPException:
            raise
        except Exception as e:
            print(f"Error updating user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update user: {str(e)}",
            )

    def delete_user(
        self, user_id: UUID, current_user: UserResponse
    ) -> DeleteUserResponse:
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
                    detail="User not found",
                )

            # 3. Validate permission
            if not self._can_manage_user(current_user, target_user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to delete this user",
                )

            # 4. Delete from auth.users (will cascade to {schema}.users)
            self.supabase.auth.admin.delete_user(str(target_user.user_id))

            return DeleteUserResponse(
                success=True,
                message=f"User {target_user.email} has been deleted",
                deleted_user_id=user_id,
            )

        except HTTPException:
            raise
        except Exception as e:
            print(f"Error deleting user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete user: {str(e)}",
            )
