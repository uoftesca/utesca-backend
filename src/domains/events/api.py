"""
Event API endpoints.

Provides REST API endpoints for event management.
"""

from fastapi import APIRouter, Depends, Query, status, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
from uuid import UUID

from domains.auth.dependencies import get_current_user, get_current_vp_or_admin, get_optional_user
from domains.auth.models import UserResponse
from .models import (
    EventCreate,
    EventUpdate,
    EventResponse,
    EventListResponse,
    EventStatus,
)
from .service import EventService


# Create router for events domain
router = APIRouter()


def get_event_service() -> EventService:
    """Dependency to get EventService instance."""
    return EventService()


@router.get("", response_model=EventListResponse)
async def get_events(
    status: Optional[EventStatus] = Query(None, description="Filter by event status"),
    current_user: Optional[UserResponse] = Depends(get_optional_user),
    service: EventService = Depends(get_event_service),
):
    """
    Get all events.

    - **Public access**: Returns only events with status='published'
    - **Authenticated access**: Returns all events based on user role
      - Directors, VPs, Co-presidents: Can see all events

    Args:
        status: Optional status filter (draft, pending_approval, published)
        Authorization header: Optional Bearer token for authenticated access

    Returns:
        EventListResponse: List of events
    """
    # If no user is authenticated, only return published events
    # For authenticated users, use the status filter if provided, otherwise return all
    if current_user is None:
        status_filter = "published"
    else:
        # Authenticated users can see all events (use status filter if provided)
        status_filter = status

    return service.get_events(status=status_filter)


@router.get("/{event_id}", response_model=EventResponse)
async def get_event_by_id(
    event_id: UUID,
    current_user: Optional[UserResponse] = Depends(get_optional_user),
    service: EventService = Depends(get_event_service),
):
    """
    Get a single event by ID.

    - **Public access**: Can only access events with status='published'
    - **Authenticated access**: Can access any event

    Args:
        event_id: Event UUID
        Authorization header: Optional Bearer token for authenticated access

    Returns:
        EventResponse: Event data

    Raises:
        404: If event not found
        403: If public user tries to access non-published event
    """
    event = service.get_event_by_id(event_id)

    # If no user is authenticated, only allow access to published events
    if current_user is None and event.status != "published":
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Access denied. This event is not published."},
        )

    return event


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    current_user: UserResponse = Depends(get_current_vp_or_admin),
    service: EventService = Depends(get_event_service),
):
    """
    Create a new event.

    - **Authorization**: Only VPs and Co-presidents can create events
    - **Directors**: Will receive 403 Forbidden

    Args:
        event_data: Event creation data
        current_user: Current authenticated user (must be VP or Co-president)

    Returns:
        EventResponse: Created event

    Raises:
        403: If user is not VP or Co-president
        400: If validation fails
        500: If creation fails
    """
    return service.create_event(event_data, created_by=current_user.id)


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: UUID,
    event_data: EventUpdate,
    current_user: UserResponse = Depends(get_current_vp_or_admin),
    service: EventService = Depends(get_event_service),
):
    """
    Update an existing event.

    - **Authorization**: Only VPs and Co-presidents can update events
    - **Directors**: Will receive 403 Forbidden

    Args:
        event_id: Event UUID
        event_data: Event update data (all fields optional)
        current_user: Current authenticated user (must be VP or Co-president)

    Returns:
        EventResponse: Updated event

    Raises:
        403: If user is not VP or Co-president
        404: If event not found
        400: If validation fails
        500: If update fails
    """
    return service.update_event(event_id, event_data)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: UUID,
    current_user: UserResponse = Depends(get_current_vp_or_admin),
    service: EventService = Depends(get_event_service),
):
    """
    Delete an event.

    - **Authorization**: Only VPs and Co-presidents can delete events
    - **Directors**: Will receive 403 Forbidden

    Args:
        event_id: Event UUID
        current_user: Current authenticated user (must be VP or Co-president)

    Returns:
        204 No Content on success

    Raises:
        403: If user is not VP or Co-president
        404: If event not found
        500: If deletion fails
    """
    service.delete_event(event_id)
    return None
