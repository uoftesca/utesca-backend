"""
User API endpoints.

This module defines the FastAPI router for user-related endpoints.
"""

from fastapi import APIRouter, status, Query, Depends
from typing import Optional
from uuid import UUID

from domains.auth.dependencies import get_current_user
from domains.auth.models import UserResponse
from .models import UserListResponse
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
def list_users(
    department_id: Optional[UUID] = Query(
        None, description="Filter by department ID"
    ),
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


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get User",
    description="Get user by ID (requires authentication)",
)
def get_user(
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


# ============================================================================
# Health Check / Test Endpoint
# ============================================================================

@router.get(
    "/status",
    summary="Users Status",
    description="Check users service status",
    tags=["Health"],
)
def users_status():
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
        },
    }
