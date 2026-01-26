"""
Announcement service - Business logic for announcement operations.

This module handles creating announcements and sending announcement emails to all users.
"""

from fastapi import HTTPException, status
from typing import Optional
from uuid import UUID
from supabase import create_client, Client
from datetime import datetime

from core.database import get_supabase_client, get_schema
from core.config import get_settings
from domains.auth.models import UserResponse
from .models import (
    CreateAnnouncementRequest,
    CreateAnnouncementResponse,
    SendAnnouncementEmailRequest,
    SendAnnouncementResponse,
    AnnouncementEmailStats,
    AnnouncementListResponse,
    AnnouncementReadResponse,
)
from .repository import AnnouncementRepository


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
        Retrieve all users from the database.

        Returns:
            List of user records

        Raises:
            HTTPException: If retrieval fails
        """
        try:
            result = (
                self.supabase
                .schema(self.schema)
                .table("users")
                .select("id, email")
                .execute()
            )
            return result.data if result.data else []
        except Exception as e:
            print(f"Error fetching users: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch users",
            )

    def _send_emails_via_supabase(
        self,
        users: list[dict],
        title: str,
        content: str,
        priority: str,
        send_to_all: bool,
    ) -> AnnouncementEmailStats:
        """
        Send announcement emails to users using Supabase Auth API.

        Args:
            users: List of user records
            title: Email subject
            content: Email message
            priority: Announcement priority
            send_to_all: If True, sends to all users. If False, respects preferences.

        Returns:
            AnnouncementEmailStats with delivery information
        """
        total_recipients = len(users)
        emails_sent = 0
        emails_skipped = 0
        failed_emails = 0

        for user in users:
            try:
                email = user.get("email")
                preference = user.get("announcement_email_preference", "all")

                # Check if user should receive this email
                should_send = send_to_all or self._should_send_to_user(preference, priority)

                if not should_send or not email:
                    emails_skipped += 1
                    continue

                # Format email subject with priority indicator if urgent
                email_subject = title if priority != "urgent" else f"[URGENT] {title}"

                try:
                    # Note: Supabase doesn't support generic email sending via admin API
                    # It only sends auth-related emails (invites, password resets)
                    # For production, integrate an email service like SendGrid, AWS SES, or SMTP
                    
                    # TODO: Implement email sending via external service
                    # For now, just log that email would be sent
                    print(f"Would send email to {email}: {email_subject}")
                    
                    # Mark as skipped since we can't actually send
                    emails_skipped += 1
                except Exception as e:
                    print(f"Failed to send email to {email}: {e}")
                    failed_emails += 1

            except Exception as e:
                print(f"Error processing user for email: {e}")
                failed_emails += 1

        return AnnouncementEmailStats(
            total_recipients=total_recipients,
            emails_sent=emails_sent,
            emails_skipped=emails_skipped,
            failed_emails=failed_emails,
        )

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

    def create_announcement(
        self,
        request: CreateAnnouncementRequest,
        current_user_id: UUID,
    ) -> CreateAnnouncementResponse:
        """
        Create a new announcement.

        Args:
            request: Create announcement request data
            current_user_id: ID of the user creating the announcement

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

            # Send emails to all users when an announcement is created (if content provided)
            if request.content:
                try:
                    users = self._get_all_users()
                    self._send_emails_via_supabase(
                        users=users,
                        title=request.title,
                        content=request.content,
                        priority=request.priority,
                        send_to_all=True,  # Always send to all when creating announcement
                    )
                except Exception as e:
                    print(f"Error sending emails for announcement: {e}")
                    # Continue even if email sending fails

            return CreateAnnouncementResponse(
                success=True,
                message=f"Announcement created successfully",
                announcement_id=announcement.id,
                created_at=announcement.created_at,
            )

        except HTTPException:
            raise
        except Exception as e:
            print(f"Error creating announcement: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create announcement: {str(e)}",
            )

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
            stats = self._send_emails_via_supabase(
                users=users,
                title=request.title,
                content=request.content,
                priority=request.priority,
                send_to_all=request.send_to_all,
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
            print(f"Error sending announcement email: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send announcement email: {str(e)}",
            )

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
            print(f"Error fetching announcements: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch announcements",
            )

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
            AnnouncementReadResponse with read record

        Raises:
            HTTPException: If operation fails
        """
        try:
            # Check if already read
            if self.repository.has_user_read(announcement_id, user_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Announcement already marked as read",
                )

            # Mark as read
            read_record = self.repository.mark_as_read(announcement_id, user_id)

            return read_record

        except HTTPException:
            raise
        except Exception as e:
            print(f"Error marking announcement as read: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to mark announcement as read",
            )
