"""
Pydantic models for departments domain.

These models define the request/response schemas for department endpoints.
"""

from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
from uuid import UUID


# ============================================================================
# Response Models
# ============================================================================

class DepartmentResponse(BaseModel):
    """Single department response."""

    id: UUID
    name: str
    year: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DepartmentListResponse(BaseModel):
    """List of departments with metadata."""

    year: Optional[int] = None  # None if returning all years
    departments: List[DepartmentResponse]


class YearsResponse(BaseModel):
    """Available years response."""

    years: List[int]
    current_year: int
