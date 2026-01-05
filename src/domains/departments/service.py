"""
Department service - Business logic for department operations.

This module handles business logic for department management.
"""

from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client, create_client

from core.config import get_settings
from core.database import get_schema

from .models import DepartmentListResponse, DepartmentResponse, YearsResponse
from .repository import DepartmentRepository


def get_current_academic_year() -> int:
    """
    Get the current academic year based on the date.

    UTESCA's academic year transitions on July 1st:
    - Jan 1 - Jun 30: Current calendar year
    - Jul 1 - Dec 31: Next calendar year

    Examples:
    - June 30, 2025 → 2025
    - July 1, 2025 → 2026
    - December 31, 2025 → 2026
    - January 1, 2026 → 2026

    Returns:
        Academic year (integer)
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    year = now.year

    # If we're in July or later (month >= 7), use next year
    if now.month >= 7:
        return year + 1

    return year


class DepartmentService:
    """Service class for department operations."""

    def __init__(self):
        self.settings = get_settings()
        self.schema = get_schema()
        # Use admin client to bypass RLS (endpoints are protected by authentication)
        self.supabase = self._get_admin_client()
        self.repository = DepartmentRepository(self.supabase, self.schema)

    def _get_admin_client(self) -> Client:
        """
        Get Supabase client with service role key for admin operations.

        This bypasses RLS policies. Access control is enforced at the endpoint level
        by requiring authentication.

        Returns:
            Client: Supabase client with admin privileges
        """
        return create_client(
            self.settings.SUPABASE_URL,
            self.settings.SUPABASE_SERVICE_ROLE_KEY
        )

    def get_departments(
        self, year: Optional[int] = None, all_years: bool = False
    ) -> DepartmentListResponse:
        """
        Get list of departments, optionally filtered by year.

        Args:
            year: Optional year to filter by. Defaults to current academic year if not provided.
            all_years: If True, return departments from all years (overrides year parameter)

        Returns:
            DepartmentListResponse with departments and metadata

        Raises:
            HTTPException: If retrieval fails
        """
        try:
            # If all_years is True, ignore year parameter
            if all_years:
                departments = self.repository.get_all()
                return DepartmentListResponse(year=None, departments=departments)

            # If year not provided, default to current academic year
            filter_year = year if year is not None else get_current_academic_year()

            departments = self.repository.get_all(year=filter_year)

            return DepartmentListResponse(
                year=filter_year,
                departments=departments
            )

        except HTTPException:
            raise
        except Exception as e:
            print(f"Error fetching departments: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch departments: {str(e)}",
            ) from e

    def get_department_by_id(self, department_id: UUID) -> DepartmentResponse:
        """
        Get department by ID.

        Args:
            department_id: Department UUID

        Returns:
            DepartmentResponse

        Raises:
            HTTPException: If department not found or retrieval fails
        """
        try:
            department = self.repository.get_by_id(department_id)

            if not department:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Department not found",
                )

            return department

        except HTTPException:
            raise
        except Exception as e:
            print(f"Error fetching department: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch department: {str(e)}",
            ) from e

    def get_available_years(self) -> YearsResponse:
        """
        Get list of unique years that have departments.

        Returns:
            YearsResponse with list of years and current academic year

        Raises:
            HTTPException: If retrieval fails
        """
        try:
            years = self.repository.get_available_years()
            current_year = get_current_academic_year()

            return YearsResponse(
                years=years if years else [current_year],
                current_year=current_year
            )

        except HTTPException:
            raise
        except Exception as e:
            print(f"Error fetching available years: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch available years: {str(e)}",
            ) from e
