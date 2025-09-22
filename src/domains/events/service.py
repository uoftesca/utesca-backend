"""
Event domain service (business logic layer).
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from src.domains.events.repository import EventRepository
from src.domains.events.schemas import EventCreate, EventUpdate, EventResponse, EventListResponse
from src.domains.events.models import Event


class EventService:
    """Service for event business logic."""

    def __init__(self, db: Session):
        self.repository = EventRepository(db)

    def get_event(self, event_id: int) -> Optional[EventResponse]:
        """Get event by ID."""
        event = self.repository.get_by_id(event_id)
        if not event:
            return None
        return EventResponse.model_validate(event)

    def get_events(self, skip: int = 0, limit: int = 100) -> EventListResponse:
        """Get all events with pagination."""
        events = self.repository.get_all(skip=skip, limit=limit)
        total = self.repository.count()

        return EventListResponse(
            events=[EventResponse.model_validate(event) for event in events],
            total=total,
            page=(skip // limit) + 1,
            size=limit
        )

    def get_featured_events(self) -> List[EventResponse]:
        """Get featured events."""
        events = self.repository.get_featured()
        return [EventResponse.model_validate(event) for event in events]

    def create_event(self, event_data: EventCreate) -> EventResponse:
        """Create a new event."""
        event = self.repository.create(event_data)
        return EventResponse.model_validate(event)

    def update_event(self, event_id: int, event_data: EventUpdate) -> Optional[EventResponse]:
        """Update an existing event."""
        event = self.repository.update(event_id, event_data)
        if not event:
            return None
        return EventResponse.model_validate(event)

    def delete_event(self, event_id: int) -> bool:
        """Delete an event."""
        return self.repository.delete(event_id)
