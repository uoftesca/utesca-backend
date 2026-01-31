"""
Email service for sending transactional emails via Resend.

This service provides methods for sending various email types including
confirmations, announcements, and notifications.
"""

import logging
from typing import List, Optional

from core.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via Resend API."""

    def __init__(self):
        """Initialize email service with Resend API key."""
        self.settings = get_settings()
        self.api_key = self.settings.RESEND_API_KEY
        
        # Initialize Resend client if API key exists
        if self.api_key:
            try:
                from resend import Resend
                self.client = Resend(api_key=self.api_key)
            except ImportError:
                logger.warning("Resend package not installed. Email sending will be unavailable.")
                self.client = None
        else:
            logger.warning("RESEND_API_KEY not configured. Email sending will be unavailable.")
            self.client = None

    def _is_enabled(self) -> bool:
        """Check if email service is properly configured."""
        return self.client is not None

    def send_announcement(
        self,
        to: str,
        full_name: Optional[str],
        announcement_title: str,
        announcement_content: str,
        priority: str = "normal",
    ) -> bool:
        """
        Send an announcement email to a user.

        Args:
            to: Recipient email address
            full_name: Recipient's full name (optional)
            announcement_title: Title of the announcement
            announcement_content: Content of the announcement
            priority: Priority level ('normal' or 'urgent')

        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self._is_enabled():
            logger.warning(f"Email service not configured. Would send announcement to {to}")
            return False

        try:
            # Format the subject with priority indicator
            subject = announcement_title
            if priority == "urgent":
                subject = f"[URGENT] {announcement_title}"

            # Build greeting
            greeting = f"Hi {full_name}," if full_name else "Hello,"

            # Create email body
            email_body = f"""
{greeting}

{announcement_content}

Best regards,
UTESCA Team
            """.strip()

            # Send via Resend
            response = self.client.emails.send(
                from_="noreply@utesca.ca",
                to=[to],
                subject=subject,
                text=email_body,
                html=self._format_html(
                    greeting=greeting,
                    content=announcement_content,
                    priority=priority,
                ),
            )

            if response and response.get("id"):
                logger.info(f"Announcement email sent successfully to {to}")
                return True
            else:
                logger.warning(f"Resend API response invalid for email to {to}")
                return False

        except Exception as e:
            logger.error(f"Failed to send announcement email to {to}: {str(e)}", exc_info=True)
            return False

    def send_registration_confirmation(
        self,
        to: str,
        full_name: Optional[str],
        event_title: str,
        event_datetime: str,
        event_location: str,
        registration_id: str,
        base_url: str,
    ) -> bool:
        """
        Send registration confirmation email.

        Args:
            to: Recipient email
            full_name: Recipient name
            event_title: Event title
            event_datetime: Event date/time
            event_location: Event location
            registration_id: Registration ID
            base_url: Base URL for RSVP links

        Returns:
            True if sent successfully
        """
        if not self._is_enabled():
            logger.warning(f"Email service not configured. Would send confirmation to {to}")
            return False

        try:
            greeting = f"Hi {full_name}," if full_name else "Hello,"
            rsvp_link = f"{base_url}/rsvp/{registration_id}"

            email_body = f"""
{greeting}

Thank you for registering for {event_title}!

Event Details:
- Date & Time: {event_datetime}
- Location: {event_location}

Please confirm your attendance: {rsvp_link}

See you there!
UTESCA Team
            """.strip()

            response = self.client.emails.send(
                from_="noreply@utesca.ca",
                to=[to],
                subject=f"Registration Confirmed: {event_title}",
                text=email_body,
            )

            if response and response.get("id"):
                logger.info(f"Confirmation email sent to {to}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to send confirmation email to {to}: {str(e)}", exc_info=True)
            return False

    def send_application_received(
        self,
        to: str,
        full_name: Optional[str],
        event_title: str,
        event_datetime: str,
        event_location: str,
    ) -> bool:
        """
        Send application received email (for pending approval).

        Args:
            to: Recipient email
            full_name: Recipient name
            event_title: Event title
            event_datetime: Event date/time
            event_location: Event location

        Returns:
            True if sent successfully
        """
        if not self._is_enabled():
            logger.warning(f"Email service not configured. Would send application email to {to}")
            return False

        try:
            greeting = f"Hi {full_name}," if full_name else "Hello,"

            email_body = f"""
{greeting}

We've received your application for {event_title}!

Event Details:
- Date & Time: {event_datetime}
- Location: {event_location}

Your application is under review. We'll notify you once it's been approved.

UTESCA Team
            """.strip()

            response = self.client.emails.send(
                from_="noreply@utesca.ca",
                to=[to],
                subject=f"Application Received: {event_title}",
                text=email_body,
            )

            if response and response.get("id"):
                logger.info(f"Application received email sent to {to}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to send application email to {to}: {str(e)}", exc_info=True)
            return False

    def send_attendance_confirmed(
        self,
        to: str,
        full_name: Optional[str],
        event_title: str,
        event_datetime: str,
        event_location: str,
        registration_id: str,
        base_url: str,
    ) -> bool:
        """Send attendance confirmed email."""
        if not self._is_enabled():
            return False

        try:
            greeting = f"Hi {full_name}," if full_name else "Hello,"

            email_body = f"""
{greeting}

We've confirmed your attendance for {event_title}!

Event Details:
- Date & Time: {event_datetime}
- Location: {event_location}

See you there!
UTESCA Team
            """.strip()

            response = self.client.emails.send(
                from_="noreply@utesca.ca",
                to=[to],
                subject=f"Attendance Confirmed: {event_title}",
                text=email_body,
            )

            return bool(response and response.get("id"))
        except Exception as e:
            logger.error(f"Failed to send attendance confirmed email: {str(e)}", exc_info=True)
            return False

    def send_attendance_declined(
        self,
        to: str,
        full_name: Optional[str],
        event_title: str,
        event_datetime: str,
        event_location: str,
    ) -> bool:
        """Send attendance declined email."""
        if not self._is_enabled():
            return False

        try:
            greeting = f"Hi {full_name}," if full_name else "Hello,"

            email_body = f"""
{greeting}

We've recorded that you won't be attending {event_title}.

If you change your mind, feel free to reach out!

UTESCA Team
            """.strip()

            response = self.client.emails.send(
                from_="noreply@utesca.ca",
                to=[to],
                subject=f"Attendance Declined: {event_title}",
                text=email_body,
            )

            return bool(response and response.get("id"))
        except Exception as e:
            logger.error(f"Failed to send attendance declined email: {str(e)}", exc_info=True)
            return False

    def send_rsvp_decline_notification(
        self,
        to_emails: List[str],
        attendee_name: Optional[str],
        attendee_email: str,
        event_title: str,
        event_datetime: str,
        event_location: str,
        previous_status: str,
    ) -> bool:
        """Send RSVP decline notification to subscribed users."""
        if not self._is_enabled():
            return False

        try:
            email_body = f"""
An attendee has declined for {event_title}.

Attendee: {attendee_name or attendee_email}
Event: {event_title}
Date & Time: {event_datetime}
Location: {event_location}

Previous Status: {previous_status}

UTESCA Team
            """.strip()

            response = self.client.emails.send(
                from_="noreply@utesca.ca",
                to=to_emails,
                subject=f"RSVP Update: {event_title}",
                text=email_body,
            )

            return bool(response and response.get("id"))
        except Exception as e:
            logger.error(f"Failed to send RSVP decline notification: {str(e)}", exc_info=True)
            return False

    def _format_html(
        self,
        greeting: str,
        content: str,
        priority: str = "normal",
    ) -> str:
        """Format email content as HTML."""
        return f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2>{greeting}</h2>
        <div style="background-color: {'#ffe6e6' if priority == 'urgent' else '#f9f9f9'}; padding: 15px; border-radius: 5px;">
            {content}
        </div>
        <p style="margin-top: 20px; font-size: 12px; color: #666;">
            Best regards,<br>
            UTESCA Team
        </p>
    </div>
</body>
</html>
        """.strip()
