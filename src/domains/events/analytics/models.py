"""
Pydantic models for event analytics responses.
"""

from datetime import date
from typing import List

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class TimelinePoint(BaseModel):
    date: date
    count: int

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class StatusBreakdown(BaseModel):
    submitted: int
    accepted: int
    rejected: int
    confirmed: int
    not_attending: int
    checked_in: int

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class AnalyticsResponse(BaseModel):
    total_registrations: int
    by_status: StatusBreakdown
    approval_rate: float
    attendance_rate: float
    registration_timeline: List[TimelinePoint]

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

