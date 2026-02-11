"""
Data access layer for announcements.

This module handles all database operations related to announcements.
"""

from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from supabase import Client

from .models import AnnouncementReadResponse, AnnouncementResponse


class AnnouncementRepository:
    """Repository for announcement data access operations."""

    def __init__(self, client: Client, schema: str):
        """
        Initialize the repository with a Supabase client.

        Args:
            client: Supabase client instance
            schema: Database schema name ('test' or 'prod')
        """
        self.client = client
        self.schema = schema

    def create_announcement(
        self,
        title: str,
        content: Optional[str],
        priority: str,
        created_by: UUID,
        expires_at: Optional[datetime] = None,
    ) -> AnnouncementResponse:
        """
        Create a new announcement record in the database.

        Args:
            title: Announcement title
            content: Announcement content/message
            priority: Announcement priority ('normal' or 'urgent')
            created_by: ID of the user creating the announcement
            expires_at: When the announcement expires (optional)

        Returns:
            AnnouncementResponse: Created announcement record

        Raises:
            Exception: If creation fails
        """
        data: dict = {
            "title": title,
            "content": content,
            "priority": priority,
            "created_by": str(created_by),
        }

        if expires_at:
            data["expires_at"] = expires_at.isoformat()

        # Attempt insert, with graceful fallback when schema lacks optional columns
        try:
            result = self.client.schema(self.schema).table("announcements").insert(data).execute()
        except Exception as e:
            # Handle missing column in schema cache (e.g., test schema without expires_at)
            msg = str(e)
            if "PGRST204" in msg and "expires_at" in msg and "schema cache" in msg:
                # Retry without the expires_at field
                data.pop("expires_at", None)
                result = self.client.schema(self.schema).table("announcements").insert(data).execute()
            else:
                raise

        if not result.data or len(result.data) == 0:
            raise Exception("Failed to create announcement record")

        return AnnouncementResponse(**result.data[0])  # type: ignore[arg-type]

    def get_announcement(self, announcement_id: UUID) -> Optional[AnnouncementResponse]:
        """
        Get a single announcement by ID.

        Args:
            announcement_id: ID of the announcement

        Returns:
            AnnouncementResponse or None if not found
        """
        result = (
            self.client.schema(self.schema).table("announcements").select("*").eq("id", str(announcement_id)).execute()
        )

        if not result.data or len(result.data) == 0:
            return None

        return AnnouncementResponse(**result.data[0])  # type: ignore[arg-type]

    def get_all(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Tuple[List[AnnouncementResponse], int]:
        """
        Fetch all announcements with pagination.

        Args:
            limit: Number of records to return
            offset: Number of records to skip

        Returns:
            Tuple of (list of announcements, total count)
        """
        # Build query
        query = self.client.schema(self.schema).table("announcements").select("*", count="exact")  # type: ignore[arg-type]

        # Order by created_at descending (newest first)
        query = query.order("created_at", desc=True)

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

        announcements = [AnnouncementResponse(**announcement) for announcement in result.data]  # type: ignore[arg-type]

        return announcements, total_count

    def mark_as_read(
        self,
        announcement_id: UUID,
        user_id: UUID,
    ) -> AnnouncementReadResponse:
        """
        Mark an announcement as read by a user.

        Args:
            announcement_id: ID of the announcement
            user_id: ID of the user

        Returns:
            AnnouncementReadResponse: Created read record

        Raises:
            Exception: If creation fails
        """
        data = {
            "announcement_id": str(announcement_id),
            "user_id": str(user_id),
        }
        result = self.client.schema(self.schema).table("announcement_reads").insert(data).execute()

        if not result.data or len(result.data) == 0:
            raise Exception("Failed to mark announcement as read")

        return AnnouncementReadResponse(**result.data[0])  # type: ignore[arg-type]

    def get_user_reads(
        self,
        user_id: UUID,
    ) -> List[AnnouncementReadResponse]:
        """
        Get all announcements read by a user.

        Args:
            user_id: ID of the user

        Returns:
            List of announcement reads
        """
        result = (
            self.client.schema(self.schema)
            .table("announcement_reads")
            .select("*")
            .eq("user_id", str(user_id))
            .execute()
        )

        if not result.data:
            return []

        return [AnnouncementReadResponse(**read) for read in result.data]  # type: ignore[arg-type]

    def has_user_read(
        self,
        announcement_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Check if a user has read an announcement.

        Args:
            announcement_id: ID of the announcement
            user_id: ID of the user

        Returns:
            True if user has read the announcement, False otherwise
        """
        result = (
            self.client.schema(self.schema)
            .table("announcement_reads")
            .select("id")
            .eq("announcement_id", str(announcement_id))
            .eq("user_id", str(user_id))
            .execute()
        )

        return result.data is not None and len(result.data) > 0

    def update_announcement(
        self,
        announcement_id: UUID,
        title: Optional[str] = None,
        content: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> Optional[AnnouncementResponse]:
        """
        Update an announcement.

        Args:
            announcement_id: ID of the announcement to update
            title: New title (optional)
            content: New content (optional)
            priority: New priority (optional)

        Returns:
            Updated AnnouncementResponse or None if not found
        """
        data = {}
        if title is not None:
            data["title"] = title
        if content is not None:
            data["content"] = content
        if priority is not None:
            data["priority"] = priority

        if not data:
            # No updates to make, just fetch and return
            return self.get_announcement(announcement_id)

        data["updated_at"] = datetime.utcnow().isoformat()

        result = (
            self.client.schema(self.schema).table("announcements").update(data).eq("id", str(announcement_id)).execute()
        )

        if not result.data or len(result.data) == 0:
            return None

        return AnnouncementResponse(**result.data[0])  # type: ignore[arg-type]

    def delete_announcement(self, announcement_id: UUID) -> bool:
        """
        Delete an announcement.

        Args:
            announcement_id: ID of the announcement to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        result = (
            self.client.schema(self.schema).table("announcements").delete().eq("id", str(announcement_id)).execute()
        )

        return result.data is not None and len(result.data) > 0

    def get_read_count(self, announcement_id: UUID) -> int:
        """
        Get the number of users who have read an announcement.

        Args:
            announcement_id: ID of the announcement

        Returns:
            Number of reads
        """
        result = (
            self.client.schema(self.schema)
            .table("announcement_reads")
            .select("id", count="exact")  # type: ignore[arg-type]
            .eq("announcement_id", str(announcement_id))
            .execute()
        )

        return result.count if result.count is not None else 0

    def get_total_users_count(self) -> int:
        """
        Get the total number of users in the system.

        Returns:
            Total number of users
        """
        result = (
            self.client.schema(self.schema)
            .table("users")
            .select("id", count="exact")  # type: ignore[arg-type]
            .execute()
        )

        return result.count if result.count is not None else 0
