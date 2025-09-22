"""
Event domain API endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.domains.events.service import EventService
from src.domains.events.schemas import EventCreate, EventUpdate, EventResponse, EventListResponse

router = APIRouter()


def get_event_service(db: Session = Depends(get_db)) -> EventService:
    """Dependency to get event service."""
    return EventService(db)


@router.get("/", response_model=EventListResponse)
async def get_events(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of items to return"),
    service: EventService = Depends(get_event_service)
):
    """Get all events with pagination."""
    return service.get_events(skip=skip, limit=limit)


@router.get("/featured", response_model=List[EventResponse])
async def get_featured_events(
    service: EventService = Depends(get_event_service)
):
    """Get featured events."""
    return service.get_featured_events()


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    service: EventService = Depends(get_event_service)
):
    """Get event by ID."""
    event = service.get_event(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    return event


@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    service: EventService = Depends(get_event_service)
):
    """Create a new event."""
    return service.create_event(event_data)


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    event_data: EventUpdate,
    service: EventService = Depends(get_event_service)
):
    """Update an existing event."""
    event = service.update_event(event_id, event_data)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    service: EventService = Depends(get_event_service)
):
    """Delete an event."""
    success = service.delete_event(event_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
