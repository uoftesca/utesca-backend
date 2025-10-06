"""
Authentication dependencies for FastAPI endpoints.

This module provides dependency functions for authentication and authorization.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from uuid import UUID

from core.database import get_supabase_client, get_schema
from .models import UserResponse


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserResponse:
    """
    Get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        UserResponse: Current user data

    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        from core.config import get_settings
        from supabase import create_client

        settings = get_settings()
        schema = get_schema()

        # Create admin client to verify JWT
        admin_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )

        # Verify JWT token and get user
        user_response = admin_client.auth.get_user(credentials.credentials)

        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )

        auth_user = user_response.user

        # Fetch full user data from users table
        result = admin_client.schema(schema).table("users") \
            .select("*") \
            .eq("user_id", auth_user.id) \
            .execute()

        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found",
            )

        return UserResponse(**result.data[0])

    except HTTPException:
        raise
    except Exception as e:
        print(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


async def get_current_admin(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """
    Verify that the current user is a co-president (admin).

    Args:
        current_user: Current authenticated user

    Returns:
        UserResponse: Current user data (if admin)

    Raises:
        HTTPException: If user is not a co-president
    """
    if current_user.role != "co_president":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only co-presidents can perform this action",
        )

    return current_user


async def get_auth_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UUID:
    """
    Get the Supabase Auth user ID from JWT token without requiring users table entry.

    This is used for onboarding flow where user exists in auth.users but not yet in users table.

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        UUID: Supabase Auth user ID

    Raises:
        HTTPException: If token is invalid
    """
    try:
        from core.config import get_settings
        from supabase import create_client

        settings = get_settings()

        # Create admin client to verify JWT
        admin_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )

        # Verify JWT token and get user
        user_response = admin_client.auth.get_user(credentials.credentials)

        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )

        return UUID(user_response.user.id)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


async def get_current_vp_or_admin(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """
    Verify that the current user is a VP or co-president.

    Args:
        current_user: Current authenticated user

    Returns:
        UserResponse: Current user data (if VP or admin)

    Raises:
        HTTPException: If user is not a VP or co-president
    """
    if current_user.role not in ["co_president", "vp"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only VPs and co-presidents can perform this action",
        )

    return current_user
