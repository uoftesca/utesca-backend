"""
Event domain repository (data access layer).
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.domains.events.models import Event
from src.domains.events.schemas import EventCreate, EventUpdate


class EventRepository:
    """Repository for event data operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, event_id: int) -> Optional[Event]:
        """Get event by ID."""
        return self.db.query(Event).filter(Event.id == event_id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Event]:
        """Get all events with pagination."""
        return (
            self.db.query(Event)
            .order_by(desc(Event.event_date))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_featured(self) -> List[Event]:
        """Get featured events."""
        return (
            self.db.query(Event)
            .filter(Event.is_featured == True)
            .order_by(desc(Event.event_date))
            .all()
        )

    def create(self, event_data: EventCreate) -> Event:
        """Create a new event."""
        event = Event(**event_data.model_dump())
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def update(self, event_id: int, event_data: EventUpdate) -> Optional[Event]:
        """Update an existing event."""
        event = self.get_by_id(event_id)
        if not event:
            return None

        update_data = event_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(event, field, value)

        self.db.commit()
        self.db.refresh(event)
        return event

    def delete(self, event_id: int) -> bool:
        """Delete an event."""
        event = self.get_by_id(event_id)
        if not event:
            return False

        self.db.delete(event)
        self.db.commit()
        return True

    def count(self) -> int:
        """Get total count of events."""
        return self.db.query(Event).count()
