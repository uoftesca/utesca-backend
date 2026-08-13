"""
Announcement service - Business logic for announcement operations.

This module handles creating announcements and sending announcement emails to all users.
"""

import logging
from typing import Any, List, Optional, cast
from uuid import UUID

import httpx
from fastapi import BackgroundTasks, HTTPException, status
from supabase import Client, create_client

from core.config import get_settings
from core.database import get_schema

from .models import (
    AnnouncementCreate,
    AnnouncementListResponse,
    AnnouncementReadResponse,
    AnnouncementResponse,
    AnnouncementWithReadCount,
)
from .repository import AnnouncementRepository

logger = logging.getLogger(__name__)


def _redact_email(email: str) -> str:
    """
    Redact email address for logging to protect PII.

    Shows first 2 chars of local part and domain, masks the rest.
    Example: test.user@example.com -> te***@ex***

    Args:
        email: Email address to redact

    Returns:
        Redacted email string
    """
    if not email or "@" not in email:
        return "***"

    try:
        local, domain = email.split("@", 1)
        local_redacted = (local[:2] + "***") if len(local) > 2 else "***"
        domain_redacted = (domain[:2] + "***") if len(domain) > 2 else "***"
        return f"{local_redacted}@{domain_redacted}"
    except Exception:
        return "***"


class AnnouncementService:
    """Service class for announcement operations."""

    def __init__(self, user_token: Optional[str] = None):
        """
        Initialize AnnouncementService with optional user token for RLS enforcement.

        Args:
            user_token: Optional JWT token for user-scoped operations.
                       If provided, creates a client that respects RLS policies.
                       If not provided, uses service role client (for background tasks).
        """
        self.settings = get_settings()
        self.schema = get_schema()
        # Create appropriate client based on whether user token is provided
        if user_token:
            # User-scoped client - RLS policies will be enforced
            self.supabase = self._get_user_client(user_token)
        else:
            # Admin client - RLS bypassed (for background tasks like email sending)
            self.supabase = self._get_admin_client()
        self.repository = AnnouncementRepository(self.supabase, self.schema)

    def _get_admin_client(self) -> Client:
        """
        Get Supabase client with service role key for admin operations.
        This bypasses RLS policies and should only be used for background tasks.

        Returns:
            Client: Supabase client with admin privileges
        """
        return create_client(self.settings.SUPABASE_URL, self.settings.SUPABASE_SERVICE_ROLE_KEY)

    def _get_user_client(self, user_token: str) -> Client:
        """
        Get Supabase client with user JWT token for RLS-enforced operations.
        This client respects Row Level Security policies.

        Args:
            user_token: JWT token from the Authorization header

        Returns:
            Client: Supabase client with user-level access
        """
        client = create_client(
            self.settings.SUPABASE_URL,
            self.settings.SUPABASE_KEY,  # Use anon/public key, not service role
        )
        # Set the auth token for this client so RLS policies apply
        client.postgrest.auth(user_token)
        return client

    def _should_send_to_user(self, preference: str, priority: str) -> bool:
        """
        Determine if an email should be sent based on user preference.

        Args:
            preference: User's email preference ('all', 'urgent_only', 'none')
            priority: Announcement priority ('normal', 'urgent')

        Returns:
            True if email should be sent, False otherwise
        """
        if preference == "none":
            return False
        elif preference == "urgent_only":
            return priority == "urgent"
        else:  # "all"
            return True

    def _filter_recipients_by_priority(self, users: List[dict], priority: str) -> List[dict]:
        """
        Filter users based on priority level and notification preferences.

        Rules:
        - Urgent: Send to everyone regardless of preferences
        - Normal: Respect notification_preferences.announcements

        Args:
            users: List of users with notification_preferences
            priority: "urgent" or "normal"

        Returns:
            Filtered list of users who should receive the email
        """
        filtered = []
        skipped_by_pref = 0

        logger.info(f"Filtering {len(users)} users for {priority} announcement")

        for user in users:
            email = user.get("email", "unknown")
            redacted_email = _redact_email(email)

            # Check notification preferences for all priorities
            prefs = user.get("notification_preferences")
            prefs_type = type(prefs).__name__
            logger.debug(f"User {redacted_email} has notification_preferences of type: {prefs_type}")

            if isinstance(prefs, dict):
                announcements_pref = prefs.get("announcements", "all")
            else:
                announcements_pref = "all"  # Default to "all" if no preferences
                logger.debug(
                    f"User {redacted_email} has non-dict notification_preferences "
                    f"(type: {prefs_type}), defaulting to 'all'"
                )

            logger.debug(f"User {redacted_email} announcements preference: {announcements_pref}")

            if self._should_send_to_user(announcements_pref, priority):
                filtered.append(user)
                logger.debug(
                    f"Including {email} - preference allows (pref: {announcements_pref}, priority: {priority})"
                )
            else:
                skipped_by_pref += 1
                logger.debug(
                    f"Skipping {redacted_email} - preference blocks (pref: {announcements_pref}, priority: {priority})"
                )

        logger.info(f"Filtering complete: {len(filtered)} recipients, {skipped_by_pref} skipped by preferences")

        return filtered

    def _send_batch_emails_async(
        self,
        announcement_id: UUID,
        title: str,
        content: str,
        priority: str,
        base_url: str,
    ) -> None:
        """
        Send announcement notification emails in a background task.

        This is a blocking operation that runs asynchronously via FastAPI BackgroundTasks.
        It fetches all recipients, filters them, and sends emails with rate limiting.

        Note: This method uses an admin client to fetch all users, as background tasks
        need elevated privileges.

        Args:
            announcement_id: ID of the announcement
            title: Announcement title
            content: Announcement content (HTML)
            priority: "urgent" or "normal"
            base_url: Base URL for view links
        """
        try:
            # Create admin client for background task (needs to fetch all users)
            # Note: Cannot reuse self.supabase as it may be user-scoped
            admin_client = self._get_admin_client()

            # Fetch all users with their roles and preferences using admin client
            try:
                result = (
                    admin_client.schema(self.schema)
                    .table("users")
                    .select("id, email, role, notification_preferences, first_name, last_name")
                    .execute()
                )
                # supabase-py types result.data as a JSON union; this query returns
                # a list of row dictionaries.
                all_users: list[dict[str, Any]] = cast(list[dict[str, Any]], result.data or [])
            except Exception as e:
                logger.error(f"Error fetching users in background task: {e}")
                raise

            # Filter by priority and role
            recipients = self._filter_recipients_by_priority(all_users, priority)

            logger.info(
                f"Starting batch email send for announcement {announcement_id}. "
                f"Total recipients: {len(recipients)} (filtered from {len(all_users)} users)"
            )

            # Send emails with rate limiting
            self._send_announcement_emails_with_rate_limit(
                announcement_id=announcement_id,
                recipients=recipients,
                title=title,
                content=content,
                priority=priority,
                base_url=base_url,
            )

        except Exception as e:
            logger.error(
                f"Error in batch email send for announcement {announcement_id}: {str(e)}",
                exc_info=True,
            )

    def _send_announcement_emails_with_rate_limit(
        self,
        announcement_id: UUID,
        recipients: List[dict],
        title: str,
        content: str,
        priority: str,
        base_url: str,
    ) -> None:
        """
        Send announcement emails to recipients with rate limiting and logging.

        Args:
            announcement_id: ID of the announcement
            recipients: List of user records to send to
            title: Announcement title
            content: Announcement content (HTML)
            priority: "urgent" or "normal"
            base_url: Base URL for view links
        """
        from core.email import EmailService

        try:
            email_service = EmailService()
        except Exception as e:
            logger.error(f"Failed to initialize EmailService: {e}")
            return

        emails_sent = 0
        emails_skipped = 0
        failed_emails = 0

        for user in recipients:
            try:
                email = user.get("email")
                if not email:
                    emails_skipped += 1
                    continue

                # Extract user's full name if available
                first_name = user.get("first_name", "").strip() if user.get("first_name") else ""
                last_name = user.get("last_name", "").strip() if user.get("last_name") else ""
                full_name = f"{first_name} {last_name}".strip() if first_name or last_name else None

                # Send email (rate limiting handled globally in EmailService.send_email)
                success = email_service.send_announcement_notification(
                    to=email,
                    full_name=full_name,
                    announcement_title=title,
                    announcement_content=content,
                    priority=priority,
                    announcement_id=announcement_id,
                    base_url=base_url,
                )

                if success:
                    emails_sent += 1
                else:
                    failed_emails += 1

            except Exception as e:
                redacted_email = _redact_email(email) if email else "unknown"
                logger.error(
                    f"Error sending announcement email to {redacted_email}: {str(e)}",
                    exc_info=True,
                )
                failed_emails += 1

        logger.info(
            f"Batch announcement email delivery complete for {announcement_id}: "
            f"{emails_sent} sent, {emails_skipped} skipped, {failed_emails} failed "
            f"out of {len(recipients)} recipients"
        )

    def _send_discord_webhook_async(
        self, announcement_id: UUID, title: str, content: str, priority: str, base_url: str
    ) -> None:
        """
        Send a discord announcement in a background task.

        This is a blocking operation that runs asynchronously via FastAPI BackgroundTasks.
        It sends an HTTP POST request to the discord webhook URL.

        Args:
            announcement_id: ID of the announcement
            title: Announcement title
            content: Announcement content (HTML)
            priority: "urgent" or "normal"
            base_url: Base URL for view links
        """
        try:
            announcement_url = f"{base_url}/announcements/{announcement_id}"

            # Color hex codes in decimal (same colours as used in email format)
            color = 14431557 if priority == "urgent" else 812004
            description = f"{content}\n\n[View Announcement Here]({announcement_url})"

            if priority == "urgent":
                description = f"[URGENT]\n\n{description}"

            with httpx.Client() as client:
                response = client.post(
                    self.settings.DISCORD_WEBHOOK_URL,
                    json={
                        "username": "UTESCA Announcements",
                        "embeds": [
                            {
                                "title": title,
                                "color": color,
                                # TODO: Discord can't render HTML but "content" is HTML, fix this
                                "description": description,
                                "footer": {"text": "UTESCA Portal System", "icon_url": self.settings.EMAIL_LOGO_URL},
                            }
                        ],
                    },
                )

                response.raise_for_status()  # Raise exception if bad status code

        except Exception as e:
            logger.error(
                f"Error in discord webhook request for announcement {announcement_id}: {str(e)}",
                exc_info=True,
            )

    def create_announcement(
        self,
        request: AnnouncementCreate,
        current_user_id: UUID,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> AnnouncementResponse:
        """
        Create a new announcement.

        If send_email is true, queues an async background task to send email notifications
        based on priority level (urgent goes to all, normal respects user preferences).

        Args:
            request: Create announcement request data
            current_user_id: ID of the user creating the announcement
            background_tasks: FastAPI BackgroundTasks for queuing email send

        Returns:
            AnnouncementResponse with the created announcement

        Raises:
            HTTPException: If operation fails
        """
        try:
            announcement = self.repository.create_announcement(
                title=request.title,
                content=request.content,
                priority=request.priority,
                created_by=current_user_id,
            )

            if request.send_email:
                if not background_tasks:
                    logger.warning(
                        f"Email sending was requested for announcement {announcement.id}, "
                        "but BackgroundTasks is not available. Emails will not be sent."
                    )
                else:
                    try:
                        background_tasks.add_task(
                            self._send_batch_emails_async,
                            announcement_id=announcement.id,
                            title=request.title,
                            content=request.content,
                            priority=request.priority,
                            base_url=self.settings.BASE_URL_PUBLIC,
                        )
                        logger.info(f"Queued background email send for announcement {announcement.id}")
                    except Exception as e:
                        logger.error(f"Error queuing background email send for announcement {announcement.id}: {e}")
                        # Continue even if queuing fails — announcement is still created

            if not background_tasks:
                logger.warning(
                    f"Discord announcement was requested for announcement {announcement.id}, "
                    "but BackgroundTasks is not available. Discord announcement will not be sent."
                )
            else:
                try:
                    background_tasks.add_task(
                        self._send_discord_webhook_async,
                        announcement_id=announcement.id,
                        title=request.title,
                        content=request.content,
                        priority=request.priority,
                        base_url=self.settings.BASE_URL_PUBLIC,
                    )
                    logger.info(f"Queued background discord webhook request for announcement {announcement.id}")
                except Exception as e:
                    logger.info(f"Error queuing background discord webhook for announcement {announcement.id}: {e}")

            return announcement

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating announcement: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create announcement: {str(e)}",
            ) from e

    def get_announcements(
        self,
        user_id: UUID,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> AnnouncementListResponse:
        """
        Get list of announcements with read counts and per-user read status.

        Args:
            user_id: ID of the current user (for is_read status)
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            AnnouncementListResponse with announcements and metadata

        Raises:
            HTTPException: If retrieval fails
        """
        try:
            limit = None
            offset = None

            if page is not None and page_size is not None:
                if page < 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Page must be >= 1",
                    )
                if page_size < 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Page size must be >= 1",
                    )
                limit = page_size
                offset = (page - 1) * page_size

            announcements, total = self.repository.get_all(limit=limit, offset=offset)

            # Fetch aggregates in 2 queries regardless of announcement count
            read_counts = self.repository.get_all_read_counts()
            user_reads = self.repository.get_user_reads(user_id)
            read_by_user = {str(r.announcement_id) for r in user_reads}
            total_users = self.repository.get_total_users_count()

            items = [
                AnnouncementWithReadCount(
                    **a.model_dump(exclude={"is_read"}),
                    is_read=str(a.id) in read_by_user,
                    total_reads=read_counts.get(str(a.id), 0),
                    unread_count=total_users - read_counts.get(str(a.id), 0),
                )
                for a in announcements
            ]

            return AnnouncementListResponse(
                total=total,
                announcements=items,
                page=page,
                page_size=page_size,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching announcements: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch announcements",
            ) from e

    def mark_as_read(
        self,
        announcement_id: UUID,
        user_id: UUID,
    ) -> AnnouncementReadResponse:
        """
        Mark an announcement as read by a user.

        This operation is idempotent - if already read, returns existing read record.

        Args:
            announcement_id: ID of the announcement
            user_id: ID of the user

        Returns:
            AnnouncementReadResponse with read record

        Raises:
            HTTPException: If operation fails
        """
        try:
            # Check if already read
            if self.repository.has_user_read(announcement_id, user_id):
                # Idempotent: return existing read record
                reads = self.repository.get_user_reads(user_id)
                for read in reads:
                    if str(read.announcement_id) == str(announcement_id):
                        return read
                # If not found in list (shouldn't happen), create new one
                logger.warning(
                    f"has_user_read returned True but no record found for announcement {announcement_id} user {user_id}"
                )

            # Mark as read
            read_record = self.repository.mark_as_read(announcement_id, user_id)

            return read_record

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error marking announcement as read: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to mark announcement as read",
            ) from e

    def get_announcement(
        self,
        announcement_id: UUID,
        current_user_id: UUID,
    ):
        """
        Get a single announcement with read status for current user.

        Args:
            announcement_id: ID of the announcement
            current_user_id: ID of the current user

        Returns:
            AnnouncementResponse with is_read field populated

        Raises:
            HTTPException: If announcement not found
        """
        try:
            announcement = self.repository.get_announcement(announcement_id)
            if not announcement:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Announcement not found",
                )

            # Check if current user has read it
            announcement.is_read = self.repository.has_user_read(announcement_id, current_user_id)

            return announcement

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching announcement: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch announcement",
            ) from e

    def _check_update_delete_permission(
        self,
        announcement: AnnouncementResponse,
        current_user_id: UUID,
    ) -> None:
        """
        Check if the current user has permission to update/delete an announcement.

        Permission is granted if:
        - User is a co-president, OR
        - User is the creator of the announcement

        Args:
            announcement: The announcement to check permission for
            current_user_id: ID of the current user

        Raises:
            HTTPException: If user lacks permission
        """
        # Get current user's role from the database
        try:
            user_result = (
                self.supabase.schema(self.schema).table("users").select("role").eq("id", str(current_user_id)).execute()
            )

            # supabase-py types `data` as a JSON union, so we need to narrow it.
            data = user_result.data
            if not isinstance(data, list) or not data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )

            first_row = data[0]
            if not isinstance(first_row, dict):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Unexpected user row format",
                )

            role_value = first_row.get("role")
            user_role = role_value if isinstance(role_value, str) else None

            # Check permission: co-president OR creator
            is_co_president = user_role == "co_president"
            is_creator = str(announcement.created_by) == str(current_user_id)

            if not (is_co_president or is_creator):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only co-presidents or the announcement creator can perform this action",
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error checking user permissions: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to verify permissions",
            ) from e

    def update_announcement(
        self,
        announcement_id: UUID,
        title: Optional[str],
        content: Optional[str],
        priority: Optional[str],
        current_user_id: UUID,
    ):
        """
        Update an announcement.

        Args:
            announcement_id: ID of the announcement
            title: New title (optional)
            content: New content (optional)
            priority: New priority (optional)
            current_user_id: ID of the current user

        Returns:
            Updated AnnouncementResponse

        Raises:
            HTTPException: If announcement not found or user not authorized
        """
        try:
            # Get existing announcement to check ownership
            announcement = self.repository.get_announcement(announcement_id)
            if not announcement:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Announcement not found",
                )

            # Explicit permission check (service uses admin client that bypasses RLS)
            self._check_update_delete_permission(announcement, current_user_id)

            # Update announcement
            updated = self.repository.update_announcement(
                announcement_id=announcement_id,
                title=title,
                content=content,
                priority=priority,
            )

            if not updated:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Announcement not found or you don't have permission to update it",
                )

            return updated

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating announcement: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update announcement",
            ) from e

    def delete_announcement(
        self,
        announcement_id: UUID,
        current_user_id: UUID,
    ) -> dict:
        """
        Delete an announcement.

        Args:
            announcement_id: ID of the announcement
            current_user_id: ID of the current user

        Returns:
            Success message

        Raises:
            HTTPException: If announcement not found or user not authorized
        """
        try:
            # Check if announcement exists
            announcement = self.repository.get_announcement(announcement_id)
            if not announcement:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Announcement not found",
                )

            # Explicit permission check (service uses admin client that bypasses RLS)
            self._check_update_delete_permission(announcement, current_user_id)

            # Delete announcement
            deleted = self.repository.delete_announcement(announcement_id)

            if not deleted:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Announcement not found or you don't have permission to delete it",
                )

            return {"message": "Announcement deleted successfully"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting announcement: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete announcement",
            ) from e
