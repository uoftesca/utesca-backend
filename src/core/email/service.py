"""
Email service for sending transactional emails via Resend.
"""

import logging
import threading
import time
from typing import List, Optional

import resend

from core.config import get_settings
from domains.events.models import EmailTemplate

from .templates import (
    build_application_accepted_email,
    build_application_received_email,
    build_application_rejected_email,
    build_attendance_confirmed_email,
    build_attendance_declined_email,
    build_confirmation_email,
    build_custom_email_from_template,
    build_rsvp_decline_notification,
)

logger = logging.getLogger(__name__)

# Global rate limiting state (module-level, shared across all EmailService instances)
# Protects against exceeding Resend's 2 requests/second limit across concurrent operations
_email_rate_limiter_lock = threading.Lock()
_last_email_send_time: float = 0.0


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
        Send an email using Resend with global rate limiting.

        Rate limiting ensures we don't exceed Resend's 2 requests/second limit
        across all concurrent email operations system-wide. Uses thread-safe
        global state to enforce minimum interval between sends.

        Args:
            to: Recipient email address
            subject: Email subject line
            html_body: HTML email content
            text_body: Plain text fallback (optional)

        Returns:
            True if sent successfully, False otherwise
        """
        global _last_email_send_time

        settings = get_settings()
        min_interval = 1.0 / settings.EMAIL_RATE_LIMIT_RPS  # ~0.556 seconds for 1.8 RPS

        # Thread-safe rate limiting: enforce minimum interval between sends
        with _email_rate_limiter_lock:
            now = time.time()
            time_since_last = now - _last_email_send_time

            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                logger.debug(f"Rate limiting: sleeping {sleep_time:.3f}s before sending email to {to}")
                time.sleep(sleep_time)

            # Update timestamp while still holding lock to maintain strict ordering
            _last_email_send_time = time.time()

        # Send email via Resend (rate limiting complete, lock released)
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

    def send_application_acceptance(
        self,
        to: str,
        full_name: Optional[str],
        event_title: str,
        event_datetime: str,
        event_location: str,
        registration_id: str,
        base_url: str,
        custom_template: Optional[EmailTemplate] = None,
    ) -> bool:
        """
        Send application acceptance email (manual review).

        Uses custom template if provided, otherwise uses system default.

        Args:
            to: Recipient email
            full_name: Applicant's name (None if not available)
            event_title: Event title
            event_datetime: Formatted datetime string (Toronto time)
            event_location: Event location
            registration_id: Registration ID for RSVP link
            base_url: Base URL for RSVP link
            custom_template: Optional custom email template

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if custom_template:
                # Use custom template
                html_body, text_body, subject = build_custom_email_from_template(
                    template_subject=custom_template.subject,
                    template_body=custom_template.body,
                    full_name=full_name,
                    event_title=event_title,
                    event_datetime=event_datetime,
                    event_location=event_location,
                    registration_id=registration_id,
                    base_url=base_url,
                    email_type="acceptance",
                )
            else:
                # Use system default
                subject = f"[ACTION REQUIRED] Application Accepted: {event_title}"
                html_body, text_body = build_application_accepted_email(
                    full_name=full_name,
                    event_title=event_title,
                    event_datetime=event_datetime,
                    event_location=event_location,
                    registration_id=registration_id,
                    base_url=base_url,
                )
        except Exception as e:
            logger.error(f"Failed to build acceptance email template: {e}", exc_info=True)
            return False

        return self.send_email(
            to=to,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

    def send_application_rejection(
        self,
        to: str,
        full_name: Optional[str],
        event_title: str,
        event_datetime: str,
        event_location: str,
        custom_template: Optional[EmailTemplate] = None,
    ) -> bool:
        """
        Send application rejection email (manual review).

        Uses custom template if provided, otherwise uses system default.

        Args:
            to: Recipient email
            full_name: Applicant's name (None if not available)
            event_title: Event title
            event_datetime: Formatted datetime string (Toronto time)
            event_location: Event location
            custom_template: Optional custom email template

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if custom_template:
                # Use custom template
                html_body, text_body, subject = build_custom_email_from_template(
                    template_subject=custom_template.subject,
                    template_body=custom_template.body,
                    full_name=full_name,
                    event_title=event_title,
                    event_datetime=event_datetime,
                    event_location=event_location,
                    registration_id="",  # Not used for rejections
                    base_url="",  # Not used for rejections
                    email_type="rejection",
                )
            else:
                # Use system default
                subject = f"Application Status Update: {event_title}"
                html_body, text_body = build_application_rejected_email(
                    full_name=full_name,
                    event_title=event_title,
                    event_datetime=event_datetime,
                    event_location=event_location,
                )
        except Exception as e:
            logger.error(f"Failed to build rejection email template: {e}", exc_info=True)
            return False

        return self.send_email(
            to=to,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )
