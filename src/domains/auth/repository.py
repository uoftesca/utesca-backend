"""
Data access layer for user authentication and profile management.

This module handles all database operations related to users,
separating data access from business logic and authentication concerns.
"""

from typing import Optional, cast
from uuid import UUID

from supabase import Client

from .models import UserResponse


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

    def get_by_auth_id(self, auth_user_id: UUID) -> Optional[UserResponse]:
        """
        Fetch user by Supabase Auth user ID.

        Args:
            auth_user_id: Supabase Auth user ID

        Returns:
            UserResponse if found, None otherwise
        """
        result = self.client.schema(self.schema).table("users").select("*").eq("user_id", str(auth_user_id)).execute()

        if not result.data or len(result.data) == 0:
            return None

        return UserResponse(**cast(dict, result.data[0]))

    def get_by_id(self, user_id: UUID) -> Optional[UserResponse]:
        """
        Fetch user by internal user ID.

        Args:
            user_id: Internal user ID (primary key)

        Returns:
            UserResponse if found, None otherwise
        """
        result = self.client.schema(self.schema).table("users").select("*").eq("id", str(user_id)).execute()

        if not result.data or len(result.data) == 0:
            return None

        return UserResponse(**cast(dict, result.data[0]))

    def get_by_email(self, email: str) -> Optional[UserResponse]:
        """
        Fetch user by email address.

        Args:
            email: User's email address

        Returns:
            UserResponse if found, None otherwise
        """
        result = self.client.schema(self.schema).table("users").select("*").eq("email", email.lower()).execute()

        if not result.data or len(result.data) == 0:
            return None

        return UserResponse(**cast(dict, result.data[0]))
