"""
Event service - Business logic for event management operations.

This module handles business logic for event management.
"""

import logging
from fastapi import HTTPException, status
from typing import Optional
from uuid import UUID
from supabase import create_client, Client

from core.database import get_schema
from core.config import get_settings
from utils.google_drive_service import generate_direct_link
from .models import (
    EventResponse,
    EventCreate,
    EventUpdate,
    EventListResponse,
    EventStatus,
)
from .repository import EventRepository

# Set up logger for this module
logger = logging.getLogger(__name__)


class EventService:
    """Service class for event management operations."""

    def __init__(self):
        self.settings = get_settings()
        self.schema = get_schema()
        # Use admin client to bypass RLS (endpoints are protected by authentication)
        self.supabase = self._get_admin_client()
        self.repository = EventRepository(self.supabase, self.schema)

    def _get_admin_client(self) -> Client:
        """
        Get Supabase client with service role key for admin operations.

        Returns:
            Client: Supabase client with admin privileges
        """
        return create_client(
            self.settings.SUPABASE_URL, self.settings.SUPABASE_SERVICE_ROLE_KEY
        )

    def _convert_google_drive_url_if_needed(self, url: Optional[str]) -> Optional[str]:
        """
        Convert Google Drive URL to direct download link if needed.

        Args:
            url: Image URL (may be None)

        Returns:
            Direct download URL if conversion successful, original URL otherwise
        """
        if not url:
            return url

        # Check if it's a Google Drive URL
        if "drive.google.com" not in url:
            return url

        # Check if it's already a direct download link
        if "uc?export=download" in url:
            return url

        # Convert to direct download link
        result = generate_direct_link(url)
        if result.error:
            # If conversion fails, log the error but use original URL
            # This allows the operation to proceed even if conversion fails
            logger.warning(
                f"Failed to convert Google Drive URL to direct download link: {result.error}. "
                f"Original URL: {url}. Using original URL."
            )
            return url

        return result.direct_url or url

    def get_events(
        self,
        status: Optional[EventStatus] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> EventListResponse:
        """
        Get all events with optional filtering.

        Args:
            status: Filter by status
            limit: Number of records to return
            offset: Number of records to skip

        Returns:
            EventListResponse: List of events
        """
        events, _ = self.repository.get_all(status=status, limit=limit, offset=offset)
        return EventListResponse(events=events)

    def get_event_by_id(self, event_id: UUID) -> EventResponse:
        """
        Get a single event by ID.

        Args:
            event_id: Event UUID

        Returns:
            EventResponse: Event data

        Raises:
            HTTPException: If event not found
        """
        event = self.repository.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with id {event_id} not found",
            )
        return event

    def create_event(self, event_data: EventCreate, created_by: UUID) -> EventResponse:
        """
        Create a new event.

        Args:
            event_data: Event creation data
            created_by: UUID of user creating the event

        Returns:
            EventResponse: Created event
        """
        try:
            # Convert Google Drive image URL to direct download link if needed
            if event_data.image_url:
                event_data.image_url = self._convert_google_drive_url_if_needed(event_data.image_url)

            return self.repository.create(event_data, created_by=created_by)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create event: {str(e)}",
            )

    def update_event(self, event_id: UUID, event_data: EventUpdate) -> EventResponse:
        """
        Update an existing event.

        Args:
            event_id: Event UUID
            event_data: Event update data

        Returns:
            EventResponse: Updated event

        Raises:
            HTTPException: If event not found
        """
        # Convert Google Drive image URL to direct download link if needed
        if event_data.image_url:
            event_data.image_url = self._convert_google_drive_url_if_needed(event_data.image_url)

        event = self.repository.update(event_id, event_data)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with id {event_id} not found",
            )
        return event

    def delete_event(self, event_id: UUID) -> None:
        """
        Delete an event.

        Args:
            event_id: Event UUID

        Raises:
            HTTPException: If event not found or deletion fails
        """
        # Check if event exists
        event = self.repository.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with id {event_id} not found",
            )

        # Delete the event
        success = self.repository.delete(event_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete event with id {event_id}",
            )

