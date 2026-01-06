"""
Data access layer for department management.

This module handles all database operations related to departments,
separating data access from business logic.
"""

from typing import List, Optional, cast
from uuid import UUID

from supabase import Client

from .models import DepartmentResponse


class DepartmentRepository:
    """Repository for department data access operations."""

    def __init__(self, client: Client, schema: str):
        """
        Initialize the repository with a Supabase client.

        Args:
            client: Supabase client instance
            schema: Database schema name ('test' or 'prod')
        """
        self.client = client
        self.schema = schema

    def get_all(self, year: Optional[int] = None) -> List[DepartmentResponse]:
        """
        Fetch all departments, optionally filtered by year.

        Args:
            year: Optional year to filter by. If None, returns all departments.

        Returns:
            List of DepartmentResponse objects
        """

        query = self.client.schema(self.schema).table("departments").select("*").order("name")

        if year is not None:
            query = query.eq("year", year)

        result = query.execute()

        if not result.data:
            return []

        return [DepartmentResponse(**cast(dict, dept)) for dept in result.data]

    def get_by_id(self, department_id: UUID) -> Optional[DepartmentResponse]:
        """
        Fetch department by ID.

        Args:
            department_id: Department UUID

        Returns:
            DepartmentResponse if found, None otherwise
        """
        result = self.client.schema(self.schema).table("departments").select("*").eq("id", str(department_id)).execute()

        if not result.data or len(result.data) == 0:
            return None

        return DepartmentResponse(**cast(dict, result.data[0]))

    def get_available_years(self) -> List[int]:
        """
        Get list of unique years that have departments.

        Returns:
            List of years (integers) in descending order
        """
        result = self.client.schema(self.schema).table("departments").select("year").execute()

        if not result.data:
            return []

        # Extract unique years and sort descending
        years: list[int] = list({cast(dict, dept)["year"] for dept in result.data})
        years.sort(reverse=True)

        return years
