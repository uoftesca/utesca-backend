"""
User API endpoints.

This module defines the FastAPI router for user-related endpoints.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from domains.auth.dependencies import get_current_user
from domains.auth.models import UserResponse

from .models import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    DeleteUserResponse,
    UpdateUserRequest,
    UserListResponse,
)
from .service import UserService

# Create router
router = APIRouter()


# ============================================================================
# User Endpoints
# ============================================================================


@router.get(
    "",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Users",
    description="Get list of users with optional filtering and pagination (requires authentication)",
)
async def list_users(
    department_id: Optional[UUID] = Query(None, description="Filter by department ID"),
    role: Optional[str] = Query(None, description="Filter by role (co_president, vp, director)"),
    year: Optional[int] = Query(None, description="Filter by year"),
    search: Optional[str] = Query(None, description="Search in name, email, or role"),
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    page_size: Optional[int] = Query(None, ge=1, le=100, description="Items per page (max 100)"),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Get list of users with optional filtering and pagination.

    **Authentication:**
    - Requires valid JWT token

    **Query Parameters:**
    - `department_id`: Filter by specific department UUID
    - `role`: Filter by role (co_president, vp, director)
    - `year`: Filter by year (requires year field in users table)
    - `search`: Search query for first_name, last_name, email, or display_role
    - `page`: Page number for pagination (default: no pagination)
    - `page_size`: Number of items per page (default: no pagination, max: 100)

    **Examples:**
    - `GET /users` → All users
    - `GET /users?role=vp` → All VPs
    - `GET /users?search=john` → Users matching "john"
    - `GET /users?page=1&page_size=10` → First 10 users
    - `GET /users?department_id=xyz&page=2&page_size=10` → Second page of department xyz

    **Returns:**
    - List of users with total count and pagination metadata
    """
    service = UserService()
    return service.get_users(
        department_id=department_id,
        role=role,
        year=year,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.put(
    "/password",
    response_model=ChangePasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Change Password",
    description="Change authenticated user's password (requires authentication)",
)
async def change_password(
    request: ChangePasswordRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Change the authenticated user's password.

    **Authentication:**
    - Requires valid JWT token

    **Request Body:**
    - `current_password`: User's current password
    - `new_password`: New password (must meet requirements)
    - `confirm_password`: Confirmation of new password (must match new_password)

    **Password Requirements:**
    - Minimum 8 characters

    **Returns:**
    - Success message

    **Errors:**
    - 400: New password does not meet requirements or passwords don't match
    - 401: Current password is incorrect
    """
    service = UserService()
    return service.change_password(request, current_user)


# ============================================================================
# Health Check / Test Endpoint
# ============================================================================


@router.get(
    "/status",
    summary="Users Status",
    description="Check users service status",
    tags=["Health"],
)
async def users_status():
    """
    Check users service status.

    **Returns:**
    - Service status and configuration info
    """
    from core.config import get_settings
    from core.database import get_schema

    settings = get_settings()

    return {
        "status": "ok",
        "service": "users",
        "environment": settings.ENVIRONMENT,
        "schema": get_schema(),
        "endpoints": {
            "list_users": "GET /users",
            "get_user": "GET /users/{id}",
            "update_user": "PUT /users/{id}",
            "delete_user": "DELETE /users/{id}",
            "change_password": "PUT /users/password",
        },
    }


# ============================================================================
# User ID-based Endpoints (must come after static routes)
# ============================================================================


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get User",
    description="Get user by ID (requires authentication)",
)
async def get_user(
    user_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Get user by ID.

    **Authentication:**
    - Requires valid JWT token

    **Path Parameters:**
    - `user_id`: User UUID

    **Returns:**
    - User details

    **Errors:**
    - 404: User not found
    """
    service = UserService()
    return service.get_user_by_id(user_id)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Other User",
    description="Update user data (requires co-president or VP permissions)",
)
async def update_user(
    user_id: UUID,
    request: UpdateUserRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Update a user's information.

    **What This Endpoint Does:**
    - Administrative endpoint for managing official user data
    - Updates organizational fields (name, role, department)
    - Requires elevated permissions (co-president or VP)

    **Authentication & Permissions:**
    - Requires valid JWT token
    - **Co-presidents**: Can update any user's information
    - **VPs**: Can only update directors in their department

    **Editable Fields by Role:**
    - **Co-presidents** can change: `first_name`, `last_name`, `display_role`, `role`, `department_id`
    - **VPs** can change: `first_name`, `last_name`, `display_role` only

    **Path Parameters:**
    - `user_id`: User UUID to update

    **Request Body (all optional):**
    - `first_name`: User's official first name
    - `last_name`: User's official last name
    - `display_role`: User's display role title (e.g., "VP of Events", "Marketing Director")
    - `role`: User's system role - `co_president`/`vp`/`director` (co-presidents only)
    - `department_id`: User's department UUID (co-presidents only)

    **Returns:**
    - Updated user details

    **Errors:**
    - 400: No fields to update
    - 403: Insufficient permissions (not co-president/VP, or VP trying to modify non-director)
    - 404: User not found
    """
    service = UserService()
    return service.update_user(user_id, request, current_user)


@router.delete(
    "/{user_id}",
    response_model=DeleteUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete User",
    description="Delete a user from the system (requires co-president or VP with proper permissions)",
)
async def delete_user(
    user_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Delete a user from the system.

    **Authentication:**
    - Requires valid JWT token
    - Co-presidents: Can delete any user (except themselves)
    - VPs: Can only delete directors in their department

    **Path Parameters:**
    - `user_id`: User UUID to delete

    **Returns:**
    - Confirmation of deletion with deleted user ID

    **Errors:**
    - 400: Cannot delete yourself
    - 403: Insufficient permissions
    - 404: User not found

    **Note:**
    - This is a hard delete; the user will be permanently removed
    - Deletion cascades from auth.users to {schema}.users
    """
    service = UserService()
    return service.delete_user(user_id, current_user)
