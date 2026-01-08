"""
Email service for sending transactional emails via Resend.
"""

import logging
from typing import List, Optional

import resend

from core.config import get_settings

from .templates import (
    build_application_received_email,
    build_attendance_confirmed_email,
    build_attendance_declined_email,
    build_confirmation_email,
    build_rsvp_decline_notification,
)

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails using Resend API."""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.RESEND_API_KEY
        self.from_email = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>"
        self.reply_to = settings.EMAIL_REPLY_TO

        resend.api_key = self.api_key

    def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> bool:
        """
        Send an email using Resend.

        Args:
            to: Recipient email address
            subject: Email subject line
            html_body: HTML email content
            text_body: Plain text fallback (optional)

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            params: resend.Emails.SendParams = {
                "from": self.from_email,
                "to": [to],
                "subject": subject,
                "html": html_body,
                "reply_to": self.reply_to,
            }

            if text_body:
                params["text"] = text_body

            response = resend.Emails.send(params)
            logger.info(f"Email sent successfully to {to}. ID: {response.get('id')}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to}: {str(e)}", exc_info=True)
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
        Send confirmation email for auto-accepted registration.

        Args:
            to: Recipient email
            full_name: Registrant's name (None if not available)
            event_title: Event title
            event_datetime: Formatted datetime string (Toronto time)
            event_location: Event location
            registration_id: Registration ID for RSVP link
            base_url: Base URL for RSVP link

        Returns:
            True if sent successfully, False otherwise
        """
        subject = f"Registration Received: {event_title}"
        html_body, text_body = build_confirmation_email(
            full_name=full_name,
            event_title=event_title,
            event_datetime=event_datetime,
            event_location=event_location,
            registration_id=registration_id,
            base_url=base_url,
        )

        return self.send_email(to=to, subject=subject, html_body=html_body, text_body=text_body)

    def send_application_received(
        self,
        to: str,
        full_name: Optional[str],
        event_title: str,
        event_datetime: str,
        event_location: str,
    ) -> bool:
        """
        Send application received email for manual review registrations.

        Args:
            to: Recipient email
            full_name: Registrant's name (None if not available)
            event_title: Event title
            event_datetime: Formatted datetime string (Toronto time)
            event_location: Event location

        Returns:
            True if sent successfully, False otherwise
        """
        subject = f"Application Received: {event_title}"
        html_body, text_body = build_application_received_email(
            full_name=full_name,
            event_title=event_title,
            event_datetime=event_datetime,
            event_location=event_location,
        )

        return self.send_email(to=to, subject=subject, html_body=html_body, text_body=text_body)

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
        """
        Send attendance confirmation email when user confirms via RSVP page.

        Args:
            to: Recipient email
            full_name: Registrant's name (None if not available)
            event_title: Event title
            event_datetime: Formatted datetime string (Toronto time)
            event_location: Event location
            registration_id: Registration ID for RSVP link
            base_url: Base URL for RSVP link

        Returns:
            True if sent successfully, False otherwise
        """
        subject = f"You're Confirmed for {event_title}!"
        html_body, text_body = build_attendance_confirmed_email(
            full_name=full_name,
            event_title=event_title,
            event_datetime=event_datetime,
            event_location=event_location,
            registration_id=registration_id,
            base_url=base_url,
        )

        return self.send_email(to=to, subject=subject, html_body=html_body, text_body=text_body)

    def send_attendance_declined(
        self,
        to: str,
        full_name: Optional[str],
        event_title: str,
        event_datetime: str,
        event_location: str,
    ) -> bool:
        """
        Send attendance decline confirmation email when user declines via RSVP page.

        Args:
            to: Recipient email
            full_name: Registrant's name (None if not available)
            event_title: Event title
            event_datetime: Formatted datetime string (Toronto time)
            event_location: Event location

        Returns:
            True if sent successfully, False otherwise
        """
        subject = f"RSVP Response Received for {event_title}"
        html_body, text_body = build_attendance_declined_email(
            full_name=full_name,
            event_title=event_title,
            event_datetime=event_datetime,
            event_location=event_location,
        )

        return self.send_email(to=to, subject=subject, html_body=html_body, text_body=text_body)

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
        """
        Send RSVP decline notification to subscribed users.

        Sends individual emails to each recipient (Resend best practice).
        This is an internal notification for event organizers and team members.

        Args:
            to_emails: List of recipient email addresses
            attendee_name: Declining attendee's name (None if not available)
            attendee_email: Declining attendee's email address
            event_title: Event title
            event_datetime: Formatted datetime string (Toronto time)
            event_location: Event location
            previous_status: Status before decline (typically "confirmed")

        Returns:
            True if at least one email sent successfully, False otherwise
        """
        if not to_emails:
            logger.info("No recipients for RSVP decline notification")
            return False

        try:
            # Build email template
            subject = f"RSVP Declined: {attendee_name} @ {event_title}"
            html_body, text_body = build_rsvp_decline_notification(
                attendee_name=attendee_name,
                attendee_email=attendee_email,
                event_title=event_title,
                event_datetime=event_datetime,
                event_location=event_location,
                previous_status=previous_status,
            )
        except Exception as e:
            logger.error(f"Failed to build RSVP decline notification template: {e}", exc_info=True)
            return False

        # Send individual emails to each recipient (not BCC)
        success_count = 0
        for recipient in to_emails:
            success = self.send_email(
                to=recipient,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            if success:
                success_count += 1

        logger.info(f"RSVP decline notification sent to {success_count}/{len(to_emails)} recipients")
        return success_count > 0
