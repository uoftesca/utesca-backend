"""
Event domain models.

Pydantic models for event-related data structures.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class Event(BaseModel):
    """Model representing a single event."""
    title: str
    date: str
    description: Optional[str] = ""
    category: Optional[str] = ""
    registrationLink: Optional[str] = ""
    image: Optional[str] = ""
    imagePosition: Optional[str | int] = "center"
    driveLink: Optional[str] = ""


class Store(BaseModel):
    """Model representing the event store collection."""
    events: List[Event] = Field(default_factory=list)

