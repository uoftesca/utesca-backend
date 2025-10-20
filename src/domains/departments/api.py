"""
Department API endpoints.

This module defines the FastAPI router for department-related endpoints.
"""

from fastapi import APIRouter, status, Query, Depends
from typing import Optional
from uuid import UUID

from domains.auth.dependencies import get_current_user
from domains.auth.models import UserResponse
from .models import DepartmentResponse, DepartmentListResponse, YearsResponse
from .service import DepartmentService


# Create router
router = APIRouter()


# ============================================================================
# Department Endpoints
# ============================================================================

@router.get(
    "",
    response_model=DepartmentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Departments",
    description="Get list of departments, optionally filtered by year (requires authentication)",
)
async def list_departments(
    year: Optional[int] = Query(
        None,
        description="Filter by specific year. Defaults to current academic year if not provided."
    ),
    all: bool = Query(
        False,
        description="If true, return departments from all years (overrides year parameter)"
    ),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Get list of departments with optional year filtering.

    **Authentication:**
    - Requires valid JWT token

    **Default Behavior:**
    - If no parameters provided: Returns departments for current academic year
    - Academic year transitions on July 1st (e.g., July 1, 2025 → 2026)

    **Query Parameters:**
    - `year`: Filter by specific year (e.g., 2025, 2026)
    - `all`: If true, return all departments regardless of year

    **Examples:**
    - `GET /departments` → Current year departments
    - `GET /departments?year=2025` → 2025 departments
    - `GET /departments?all=true` → All departments from all years

    **Returns:**
    - List of departments with year metadata
    """
    service = DepartmentService()
    return service.get_departments(year=year, all_years=all)


@router.get(
    "/years",
    response_model=YearsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Available Years",
    description="Get list of unique years that have departments (requires authentication)",
)
async def get_available_years(
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Get list of unique years that have departments.

    Useful for frontend year selectors and dropdowns.

    **Returns:**
    - List of years (descending order)
    - Current academic year
    """
    service = DepartmentService()
    return service.get_available_years()


@router.get(
    "/status",
    summary="Departments Status",
    description="Check departments service status",
    tags=["Health"]
)
async def departments_status():
    """
    Check departments service status.

    **Returns:**
    - Service status and configuration info
    """
    from core.config import get_settings
    from core.database import get_schema

    settings = get_settings()

    return {
        "status": "ok",
        "service": "departments",
        "environment": settings.ENVIRONMENT,
        "schema": get_schema(),
        "endpoints": {
            "list_departments": "GET /departments",
            "get_available_years": "GET /departments/years",
            "get_department": "GET /departments/{id}",
        },
    }


@router.get(
    "/{department_id}",
    response_model=DepartmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Department",
    description="Get department by ID (requires authentication)",
)
async def get_department(
    department_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Get department by ID.

    **Path Parameters:**
    - `department_id`: Department UUID

    **Returns:**
    - Department details

    **Errors:**
    - 404: Department not found
    """
    service = DepartmentService()
    return service.get_department_by_id(department_id)
