"""
Announcement service - Business logic for announcement operations.

This module handles creating announcements and sending announcement emails to all users.
"""

import logging
import time
from typing import List, Optional
from uuid import UUID

from fastapi import BackgroundTasks, HTTPException, status
from supabase import Client, create_client

from core.config import get_settings
from core.database import get_schema

from .models import (
    AnnouncementEmailStats,
    AnnouncementListResponse,
    AnnouncementReadResponse,
    AnnouncementResponse,
    CreateAnnouncementRequest,
    CreateAnnouncementResponse,
    SendAnnouncementEmailRequest,
    SendAnnouncementResponse,
)
from .repository import AnnouncementRepository

logger = logging.getLogger(__name__)


class AnnouncementService:
    """Service class for announcement operations."""

    def __init__(self):
        self.settings = get_settings()
        self.schema = get_schema()
        # Use admin client to bypass RLS (endpoints are protected by authentication)
        self.supabase = self._get_admin_client()
        self.repository = AnnouncementRepository(self.supabase, self.schema)

    def _get_admin_client(self) -> Client:
        """
        Get Supabase client with service role key for admin operations.

        Returns:
            Client: Supabase client with admin privileges
        """
        return create_client(
            self.settings.SUPABASE_URL,
            self.settings.SUPABASE_SERVICE_ROLE_KEY
        )

    def _get_all_users(self) -> list[dict]:
        """
        Retrieve all users from the database with roles and notification preferences.

        Returns:
            List of user records with id, email, role, and preferences

        Raises:
            HTTPException: If retrieval fails
        """
        try:
            result = (
                self.supabase
                .schema(self.schema)
                .table("users")
                .select("id, email, role, notification_preferences, first_name, last_name")
                .execute()
            )
            return result.data if result.data else []  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Error fetching users: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch users",
            ) from e

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

            # Urgent announcements go to everyone
            if priority == "urgent":
                filtered.append(user)
                logger.debug(f"Including {email} - urgent announcement bypasses preferences")
                continue

            # Normal announcements: check notification preferences
            prefs = user.get("notification_preferences")
            logger.debug(f"User {email} notification_preferences: {prefs} (type: {type(prefs)})")

            if isinstance(prefs, dict):
                announcements_pref = prefs.get("announcements", "all")
            else:
                announcements_pref = "all"  # Default to "all" if no preferences
                logger.warning(f"User {email} has non-dict notification_preferences: {prefs}")

            logger.debug(f"User {email} announcements preference: {announcements_pref}")

            if self._should_send_to_user(announcements_pref, priority):
                filtered.append(user)
                logger.debug(
                    f"Including {email} - preference allows "
                    f"(pref: {announcements_pref}, priority: {priority})"
                )
            else:
                skipped_by_pref += 1
                logger.info(f"Skipping {email} - preference blocks (pref: {announcements_pref}, priority: {priority})")

        logger.info(
            f"Filtering complete: {len(filtered)} recipients, "
            f"{skipped_by_pref} skipped by preferences"
        )

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
        Send announcement notification emails in a background thread.

        This is a blocking operation that runs asynchronously via threading.
        It fetches all recipients, filters them, and sends emails with rate limiting.

        Args:
            announcement_id: ID of the announcement
            title: Announcement title
            content: Announcement content (HTML)
            priority: "urgent" or "normal"
            base_url: Base URL for view links
        """
        try:
            # Fetch all users with their roles and preferences
            all_users = self._get_all_users()

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

        # Rate limiting: Resend allows 2 requests/second, so 500ms between emails
        MIN_DELAY_SECONDS = 0.5
        last_send_time: float = 0.0

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

                # Rate limiting: ensure minimum delay between requests
                elapsed = time.time() - last_send_time
                if elapsed < MIN_DELAY_SECONDS:
                    time.sleep(MIN_DELAY_SECONDS - elapsed)

                last_send_time = time.time()

                # Send email
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
                logger.error(
                    f"Error sending announcement email to {email}: {str(e)}",
                    exc_info=True,
                )
                failed_emails += 1

        logger.info(
            f"Batch announcement email delivery complete for {announcement_id}: "
            f"{emails_sent} sent, {emails_skipped} skipped, {failed_emails} failed "
            f"out of {len(recipients)} recipients"
        )

    def start_batch_email_send_async(
        self,
        background_tasks: BackgroundTasks,
        announcement_id: UUID,
        title: str,
        content: str,
        priority: str,
        base_url: str,
    ) -> None:
        """
        Start batch email sending using FastAPI BackgroundTasks.

        Does NOT block the API request. Email sending happens asynchronously.

        Args:
            background_tasks: FastAPI BackgroundTasks instance
            announcement_id: ID of the announcement
            title: Announcement title
            content: Announcement content (HTML)
            priority: "urgent" or "normal"
            base_url: Base URL for view links
        """
        # Add background task to FastAPI's task queue
        background_tasks.add_task(
            self._send_batch_emails_async,
            announcement_id,
            title,
            content,
            priority,
            base_url,
        )
        logger.info(f"Scheduled background task for batch email send of announcement {announcement_id}")

    def _send_emails_via_resend(
        self,
        users: list[dict],
        title: str,
        content: str,
        priority: str,
    ) -> AnnouncementEmailStats:
        """
        Send announcement emails to users using Resend email service.

        Applies priority-based filtering. Rate-limited to respect Resend API limits.

        Args:
            users: List of user records with 'id', 'email', 'notification_preferences'
            title: Announcement title
            content: Announcement content/message
            priority: Announcement priority ('normal' or 'urgent')

        Returns:
            AnnouncementEmailStats with delivery information
        """
        from core.email import EmailService

        # Apply priority-based filtering
        users = self._filter_recipients_by_priority(users, priority)

        try:
            email_service = EmailService()
        except Exception as e:
            logger.error(f"Failed to initialize EmailService: {e}")
            return AnnouncementEmailStats(
                total_recipients=len(users),
                emails_sent=0,
                emails_skipped=0,
                failed_emails=len(users),
            )

        total_recipients = len(users)
        emails_sent = 0
        emails_skipped = 0
        failed_emails = 0

        # Rate limiting: Resend allows 2 requests/second, so 500ms between emails
        MIN_DELAY_SECONDS = 0.5
        last_send_time: float = 0.0

        for user in users:
            try:
                email = user.get("email")
                if not email:
                    emails_skipped += 1
                    continue

                # Rate limiting: ensure minimum delay between requests
                elapsed = time.time() - last_send_time
                if elapsed < MIN_DELAY_SECONDS:
                    time.sleep(MIN_DELAY_SECONDS - elapsed)

                last_send_time = time.time()

                # Extract user's full name if available
                full_name = user.get("full_name")
                if not full_name:
                    # Try to build name from first/last name fields
                    first_name = user.get("first_name", "").strip() if user.get("first_name") else ""
                    last_name = user.get("last_name", "").strip() if user.get("last_name") else ""
                    if first_name or last_name:
                        full_name = f"{first_name} {last_name}".strip()

                # Send email via Resend
                success = email_service.send_announcement_notification(
                    to=email,
                    full_name=full_name,
                    announcement_title=title,
                    announcement_content=content,
                    priority=priority,
                    announcement_id="unknown",  # No announcement ID for legacy send-email endpoint
                    base_url=self.settings.BASE_URL_PUBLIC,
                )

                if success:
                    emails_sent += 1
                    logger.info(f"Announcement email sent to {email}")
                else:
                    failed_emails += 1
                    logger.warning(f"Failed to send announcement email to {email}")

            except Exception as e:
                logger.error(f"Error sending announcement email to user: {e}", exc_info=True)
                failed_emails += 1

        logger.info(
            f"Announcement email delivery: {emails_sent} sent, "
            f"{emails_skipped} skipped, {failed_emails} failed out of {total_recipients} recipients"
        )

        return AnnouncementEmailStats(
            total_recipients=total_recipients,
            emails_sent=emails_sent,
            emails_skipped=emails_skipped,
            failed_emails=failed_emails,
        )

    def create_announcement(
        self,
        request: CreateAnnouncementRequest,
        current_user_id: UUID,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> CreateAnnouncementResponse:
        """
        Create a new announcement.

        If send_email is true, starts async background task to send emails to executives
        based on priority level (urgent goes to all, normal respects preferences).

        Args:
            request: Create announcement request data
            current_user_id: ID of the user creating the announcement
            background_tasks: FastAPI BackgroundTasks instance for async email sending

        Returns:
            CreateAnnouncementResponse with announcement ID

        Raises:
            HTTPException: If operation fails
        """
        try:
            # Create announcement in database
            announcement = self.repository.create_announcement(
                title=request.title,
                content=request.content,
                priority=request.priority,
                created_by=current_user_id,
                send_email=request.send_email,
                expires_at=request.expires_at,
            )

            # Send batch emails asynchronously when send_email is true
            if request.send_email and request.content and background_tasks:
                try:
                    self.start_batch_email_send_async(
                        background_tasks=background_tasks,
                        announcement_id=announcement.id,
                        title=request.title,
                        content=request.content,
                        priority=request.priority,
                        base_url=self.settings.BASE_URL_PUBLIC,
                    )
                    logger.info(f"Scheduled background email send for announcement {announcement.id}")
                except Exception as e:
                    logger.error(f"Error scheduling background email send for announcement {announcement.id}: {e}")
                    # Continue even if async task fails - announcement is still created

            return CreateAnnouncementResponse(
                success=True,
                message="Announcement created successfully",
                announcement_id=announcement.id,
                created_at=announcement.created_at,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating announcement: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create announcement: {str(e)}",
            ) from e

    def send_announcement_email(
        self,
        request: SendAnnouncementEmailRequest,
        current_user_id: UUID,
    ) -> SendAnnouncementResponse:
        """
        Send an announcement email to all users without creating an announcement record.

        Args:
            request: Send announcement email request data
            current_user_id: ID of the user sending the email

        Returns:
            SendAnnouncementResponse with delivery statistics

        Raises:
            HTTPException: If operation fails
        """
        try:
            # Fetch all users
            users = self._get_all_users()

            if not users:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No users found to send emails to",
                )

            # Send emails
            stats = self._send_emails_via_resend(
                users=users,
                title=request.title,
                content=request.content,
                priority=request.priority,
            )

            return SendAnnouncementResponse(
                success=stats.emails_sent > 0,
                message=f"Email sent to {stats.emails_sent} users",
                stats=stats,
                announcement_id=None,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error sending announcement email: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send announcement email: {str(e)}",
            ) from e

    def get_announcements(
        self,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> AnnouncementListResponse:
        """
        Get list of announcements with pagination.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            AnnouncementListResponse with announcements and metadata

        Raises:
            HTTPException: If retrieval fails
        """
        try:
            # Calculate offset for pagination
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

            announcements, total = self.repository.get_all(
                limit=limit,
                offset=offset,
            )

            return AnnouncementListResponse(
                total=total,
                announcements=announcements,
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
                    f"has_user_read returned True but no record found for "
                    f"announcement {announcement_id} user {user_id}"
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
                self.supabase
                .schema(self.schema)
                .table("users")
                .select("role")
                .eq("id", str(current_user_id))
                .execute()
            )

            if not user_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )

            user_role = user_result.data[0].get("role")

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
