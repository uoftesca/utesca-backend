"""
Analytics service for events.
"""

from uuid import UUID

from supabase import Client, create_client

from core.config import get_settings
from core.database import get_schema
from .models import AnalyticsResponse
from .repository import AnalyticsRepository
from ..repository import EventRepository


class AnalyticsService:
    """Business logic for event analytics."""

    def __init__(self):
        settings = get_settings()
        self.schema = get_schema()
        self.supabase: Client = create_client(
            settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
        )
        self.events_repo = EventRepository(self.supabase, self.schema)
        self.repo = AnalyticsRepository(self.supabase, self.schema)

    def get_event_analytics(self, event_id: UUID) -> AnalyticsResponse:
        event = self.events_repo.get_by_id(event_id)
        if not event:
            raise ValueError("Event not found")
        return self.repo.get_analytics(event_id)

