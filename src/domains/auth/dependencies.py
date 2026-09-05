"""
Authentication dependencies for FastAPI endpoints.

This module provides dependency functions for authentication and authorization.
"""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.database import get_schema

from .models import UserResponse
from .repository import UserRepository

security = HTTPBearer(auto_error=False)


async def _get_auth_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> UUID | tuple[int, str]:
    """
    Attempt to get the current authenticated user id from JWT token.

    If unsuccessful, return the relevant HTTP error code and message.

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        UUID | tuple[int, str]: User id if successful, otherwise error code and message
    """
    if not credentials:
        return status.HTTP_401_UNAUTHORIZED, "Missing authentication token"

    from supabase import create_client

    from core.config import get_settings

    settings = get_settings()

    # Create admin client to verify JWT
    admin_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)

    # Verify JWT token and get user
    try:
        user_response = admin_client.auth.get_claims(credentials.credentials)
    except Exception:
        return status.HTTP_401_UNAUTHORIZED, "Invalid or expired authentication credentials"

    if user_response is None or "claims" not in user_response or "sub" not in user_response["claims"]:
        return status.HTTP_401_UNAUTHORIZED, "Invalid authentication credentials"

    return UUID(user_response["claims"]["sub"])


async def _get_auth_user(
    user_id: UUID | tuple[int, str] = Depends(_get_auth_user_id),
) -> UserResponse | tuple[int, str]:
    """
    Attempt to get the current authenticated user from JWT token.

    Otherwise, return the relevant HTTP error code and message.

    Args:
        user_id: Result of _get_auth_user_id

    Returns:
        UserResponse | tuple[int, str]: User data if successful, otherwise error code and message
    """
    if not isinstance(user_id, UUID):
        return user_id

    from supabase import create_client

    from core.config import get_settings

    settings = get_settings()
    schema = get_schema()

    admin_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)

    # Fetch full user data from users table
    repository = UserRepository(admin_client, schema)
    user = repository.get_by_auth_id(user_id)

    if not user:
        return status.HTTP_404_NOT_FOUND, "User profile not found"

    return user


async def get_current_user(
    user_result: UserResponse | tuple[int, str] = Depends(_get_auth_user),
) -> UserResponse:
    """
    Get the current authenticated user from JWT token.

    Args:
        user_result: Result of _get_user

    Returns:
        UserResponse: Current user data

    Raises:
        HTTPException: If token is invalid or user not found
    """
    if isinstance(user_result, UserResponse):
        return user_result
    else:
        error_code, error_msg = user_result

        raise HTTPException(
            status_code=error_code,
            detail=error_msg,
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
    user_id: UUID | tuple[int, str] = Depends(_get_auth_user_id),
) -> UUID:
    """
    Get the Supabase Auth user ID from JWT token without requiring users table entry.

    This is used for onboarding flow where user exists in auth.users but not yet in users table.

    Args:
        user_id: Result of _get_auth_user_id

    Returns:
        UUID: Supabase Auth user ID

    Raises:
        HTTPException: If token is invalid
    """
    if isinstance(user_id, UUID):
        return user_id
    else:
        error_code, error_msg = user_id

        raise HTTPException(
            status_code=error_code,
            detail=error_msg,
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


async def get_optional_user(
    user_result: UserResponse | tuple[int, str] = Depends(_get_auth_user),
) -> UserResponse | None:
    """
    Optional authentication dependency for public endpoints.

    Returns None if no credentials provided, otherwise validates and returns user.
    This is useful for endpoints that should work both with and without authentication,
    with different behavior based on authentication status.

    Args:
        user_result: Result of get _get_auth_user

    Returns:
        UserResponse | None: User data if authenticated, None otherwise
    """
    if isinstance(user_result, UserResponse):
        return user_result
    else:
        return None


async def get_optional_user_id(
    user_id: UUID | tuple[int, str] = Depends(_get_auth_user_id),
) -> UUID | None:
    """
    Optional authentication dependency for public endpoints.

    Returns None if no credentials provided, otherwise validates and returns user id.
    This is useful for endpoints that should work both with and without authentication,
    with different behavior based on authentication status.

    Args:
        user_id: Result of get _get_auth_user_id

    Returns:
        UUID | None: User data if authenticated, None otherwise
    """
    if isinstance(user_id, UUID):
        return user_id
    else:
        return None
