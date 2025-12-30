"""
Pydantic models for attendance operations.
"""

from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CheckInRequest(BaseModel):
    """Single check-in request (portal)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class BulkCheckInRequest(BaseModel):
    """Bulk check-in request."""

    registration_ids: List[UUID]

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CheckInResponse(BaseModel):
    """Response for a check-in operation."""

    id: UUID
    checked_in: bool
    checked_in_at: datetime
    checked_in_by: UUID

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class BulkCheckInResult(BaseModel):
    """Result item in bulk check-in."""

    id: UUID
    checked_in: bool

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class BulkCheckInResponse(BaseModel):
    """Bulk check-in summary."""

    checked_in_count: int
    results: List[BulkCheckInResult]

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

