"""
Data access layer for event management.

This module handles all database operations related to events.
"""

from typing import List, Optional, Tuple
from uuid import UUID
from datetime import datetime
from supabase import Client

from .models import EventResponse, EventCreate, EventUpdate, EventStatus


class EventRepository:
    """Repository for event data access operations."""

    def __init__(self, client: Client, schema: str):
        """
        Initialize the repository with a Supabase client.

        Args:
            client: Supabase client instance
            schema: Database schema name ('test' or 'prod')
        """
        self.client = client
        self.schema = schema

    def get_all(
        self,
        status: Optional[EventStatus] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Tuple[List[EventResponse], int]:
        """
        Fetch all events with optional filtering and pagination.

        Args:
            status: Filter by status (draft, pending_approval, published)
            limit: Number of records to return
            offset: Number of records to skip

        Returns:
            Tuple of (list of events, total count)
        """
        # Build query
        query = self.client.schema(self.schema).table("events").select("*", count="exact")

        # Apply filters
        if status is not None:
            query = query.eq("status", status)

        # Order by date_time descending (most recent first)
        query = query.order("date_time", desc=True)

        # Apply pagination
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)

        result = query.execute()

        # Get total count
        total_count = result.count if result.count is not None else 0

        if not result.data:
            return [], 0

        events = [EventResponse(**event) for event in result.data]

        return events, total_count

    def get_by_id(self, event_id: UUID) -> Optional[EventResponse]:
        """
        Fetch event by ID.

        Args:
            event_id: Event UUID

        Returns:
            EventResponse if found, None otherwise
        """
        result = (
            self.client.schema(self.schema)
            .table("events")
            .select("*")
            .eq("id", str(event_id))
            .execute()
        )

        if not result.data or len(result.data) == 0:
            return None

        return EventResponse(**result.data[0])

    def create(self, event_data: EventCreate, created_by: Optional[UUID] = None) -> EventResponse:
        """
        Create a new event.

        Args:
            event_data: Event creation data
            created_by: UUID of user creating the event

        Returns:
            EventResponse: Created event
        """
        # Prepare data for insertion (use by_alias=False to get snake_case for database)
        insert_data = event_data.model_dump(exclude_none=True, by_alias=False)
        if created_by is not None:
            insert_data["created_by"] = str(created_by)

        result = (
            self.client.schema(self.schema)
            .table("events")
            .insert(insert_data)
            .execute()
        )

        if not result.data or len(result.data) == 0:
            raise ValueError("Failed to create event")

        return EventResponse(**result.data[0])

    def update(self, event_id: UUID, event_data: EventUpdate) -> Optional[EventResponse]:
        """
        Update an existing event.

        Args:
            event_id: Event UUID
            event_data: Event update data

        Returns:
            EventResponse if found and updated, None otherwise
        """
        # Prepare data for update (exclude None values, use by_alias=False to get snake_case for database)
        update_data = event_data.model_dump(exclude_none=True, by_alias=False)

        if not update_data:
            # No fields to update
            return self.get_by_id(event_id)

        result = (
            self.client.schema(self.schema)
            .table("events")
            .update(update_data)
            .eq("id", str(event_id))
            .execute()
        )

        if not result.data or len(result.data) == 0:
            return None

        return EventResponse(**result.data[0])

    def delete(self, event_id: UUID) -> bool:
        """
        Delete an event.

        Args:
            event_id: Event UUID

        Returns:
            True if deleted, False otherwise
        """
        result = (
            self.client.schema(self.schema)
            .table("events")
            .delete()
            .eq("id", str(event_id))
            .execute()
        )

        # Supabase delete returns empty data array on success
        # Check if any rows were affected by checking the result
        return result is not None
