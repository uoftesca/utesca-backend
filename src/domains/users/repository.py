"""
Data access layer for user management.

This module handles all database operations related to users.
"""

from typing import List, Optional, Tuple
from uuid import UUID

from supabase import Client

from domains.auth.models import UserResponse


class UserRepository:
    """Repository for user data access operations."""

    def __init__(self, client: Client, schema: str):
        """
        Initialize the repository with a Supabase client.

        Args:
            client: Supabase client instance
            schema: Database schema name ('test' or 'prod')
        """
        self.client = client
        self.schema = schema

    def get_all(
        self,
        department_id: Optional[UUID] = None,
        role: Optional[str] = None,
        year: Optional[int] = None,
        search: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Tuple[List[UserResponse], int]:
        """
        Fetch all users with optional filtering and pagination.

        Args:
            department_id: Filter by department
            role: Filter by role (co_president, vp, director)
            year: Filter by year (TODO: requires year field in users table)
            search: Search in first_name, last_name, email, display_role
            limit: Number of records to return
            offset: Number of records to skip

        Returns:
            Tuple of (list of users, total count)
        """
        # Build query
        query = self.client.schema(self.schema).table("users").select("*", count="exact")

        # Apply filters
        if department_id is not None:
            query = query.eq("department_id", str(department_id))

        if role is not None:
            query = query.eq("role", role)

        # TODO: Add year filter when year column is added to users table
        # if year is not None:
        #     query = query.eq("year", year)

        # Search filter (searches multiple fields)
        if search:
            search_lower = search.lower()
            # Supabase doesn't support OR with ilike, so we do client-side filtering
            # For now, we'll fetch all and filter in Python
            # TODO: Consider using PostgreSQL full-text search for better performance
            pass

        # Order by created_at descending (newest first)
        query = query.order("created_at", desc=True)

        # Apply pagination
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)

        result = query.execute()

        # Get total count
        total_count = result.count if result.count is not None else 0

        if not result.data:
            return [], 0

        users = [UserResponse(**user) for user in result.data]

        # Client-side search filter if search query provided
        if search:
            search_lower = search.lower()
            users = [
                user
                for user in users
                if (
                    search_lower in user.first_name.lower()
                    or search_lower in user.last_name.lower()
                    or search_lower in user.email.lower()
                    or search_lower in user.display_role.lower()
                )
            ]
            total_count = len(users)

        return users, total_count

    def get_by_id(self, user_id: UUID) -> Optional[UserResponse]:
        """
        Fetch user by ID.

        Args:
            user_id: User UUID

        Returns:
            UserResponse if found, None otherwise
        """
        result = self.client.schema(self.schema).table("users").select("*").eq("id", str(user_id)).execute()

        if not result.data or len(result.data) == 0:
            return None

        return UserResponse(**result.data[0])

    def get_users_with_notification_enabled(self, notification_type: str) -> List[UserResponse]:
        """
        Fetch all users who have a specific notification type enabled.

        Uses PostgreSQL JSONB querying to filter by notification_preferences.

        Args:
            notification_type: Key in notification_preferences JSONB
                              (e.g., 'rsvp_changes', 'new_application_submitted')

        Returns:
            List of users with notification enabled for the specified type
        """
        # PostgreSQL JSONB query: notification_preferences->>'rsvp_changes' = 'true'
        result = (
            self.client.schema(self.schema)
            .table("users")
            .select("*")
            .eq(f"notification_preferences->>{notification_type}", "true")
            .execute()
        )

        if not result.data:
            return []

        return [UserResponse(**user) for user in result.data]

    def update(self, user_id: UUID, update_data: dict) -> Optional[UserResponse]:
        """
        Update user by ID.

        Args:
            user_id: User UUID
            update_data: Dictionary of fields to update

        Returns:
            Updated UserResponse if found, None otherwise
        """
        result = self.client.schema(self.schema).table("users").update(update_data).eq("id", str(user_id)).execute()

        if not result.data or len(result.data) == 0:
            return None

        return UserResponse(**result.data[0])

    def delete(self, user_id: UUID) -> bool:
        """
        Delete user by ID.

        Note: This only deletes from the users table. For full deletion
        including auth.users, use the Supabase admin API.

        Args:
            user_id: User UUID

        Returns:
            True if user was deleted, False if not found
        """
        result = self.client.schema(self.schema).table("users").delete().eq("id", str(user_id)).execute()

        return len(result.data) > 0 if result.data else False
