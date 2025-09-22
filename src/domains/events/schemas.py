"""
Event domain schemas (Pydantic models for API).
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl


class EventBase(BaseModel):
    """Base event schema."""
    title: str
    description: Optional[str] = None
    event_date: datetime
    location: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    registration_url: Optional[HttpUrl] = None
    is_featured: bool = False
    max_attendees: Optional[int] = None


class EventCreate(EventBase):
    """Event creation schema."""
    pass


class EventUpdate(BaseModel):
    """Event update schema."""
    title: Optional[str] = None
    description: Optional[str] = None
    event_date: Optional[datetime] = None
    location: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    registration_url: Optional[HttpUrl] = None
    is_featured: Optional[bool] = None
    max_attendees: Optional[int] = None


class EventResponse(EventBase):
    """Event response schema."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    """Event list response schema."""
    events: list[EventResponse]
    total: int
    page: int
    size: int
