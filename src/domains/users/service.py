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
from .models import UserListResponse
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
