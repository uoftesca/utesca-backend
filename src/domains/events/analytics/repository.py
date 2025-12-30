"""
Repository for event analytics queries.
"""

from collections import defaultdict
from datetime import date
from uuid import UUID

from supabase import Client

from .models import AnalyticsResponse, StatusBreakdown, TimelinePoint


class AnalyticsRepository:
    """Data access for analytics calculations."""

    def __init__(self, client: Client, schema: str):
        self.client = client
        self.schema = schema

    def get_status_counts(self, event_id: UUID) -> StatusBreakdown:
        result = (
            self.client.schema(self.schema)
            .rpc("get_event_registration_stats", {"p_event_id": str(event_id)})
            .execute()
        )
        data = (result.data or [{}])[0]
        return StatusBreakdown(
            submitted=int(data.get("submitted_count", 0) or 0),
            accepted=int(data.get("accepted_count", 0) or 0),
            rejected=int(data.get("rejected_count", 0) or 0),
            confirmed=int(data.get("confirmed_count", 0) or 0),
            checked_in=int(data.get("checked_in_count", 0) or 0),
        )

    def get_timeline(self, event_id: UUID) -> list[TimelinePoint]:
        result = (
            self.client.schema(self.schema)
            .table("event_registrations")
            .select("submitted_at")
            .eq("event_id", str(event_id))
            .execute()
        )
        counts: dict[str, int] = defaultdict(int)
        for row in result.data or []:
            submitted_at = row.get("submitted_at")
            if not submitted_at:
                continue
            day = submitted_at[:10] if isinstance(submitted_at, str) else submitted_at.date().isoformat()
            counts[day] += 1
        return [TimelinePoint(date=date.fromisoformat(day), count=count) for day, count in sorted(counts.items())]

    def get_analytics(self, event_id: UUID) -> AnalyticsResponse:
        breakdown = self.get_status_counts(event_id)
        total = (
            breakdown.submitted
            + breakdown.accepted
            + breakdown.rejected
            + breakdown.confirmed
        )
        approval_rate = (
            ((breakdown.accepted + breakdown.rejected) / total) * 100 if total else 0
        )
        attendance_rate = (
            (breakdown.checked_in / breakdown.confirmed) * 100 if breakdown.confirmed else 0
        )
        timeline = self.get_timeline(event_id)
        return AnalyticsResponse(
            total_registrations=total,
            by_status=breakdown,
            approval_rate=round(approval_rate, 2),
            attendance_rate=round(attendance_rate, 2),
            registration_timeline=timeline,
        )

