"""
Email template builders for various email types.
Returns both HTML and plain text versions for better email client compatibility.
"""

from typing import Optional, Tuple

from core.config import get_settings

# Load configuration
_settings = get_settings()
LOGO_URL = _settings.EMAIL_LOGO_URL

# Brand colors
UTESCA_BLUE = "#121921"


def _build_email_html(header_title: str, body_content: str) -> str:
    """
    Build complete HTML email with common header and footer.

    Args:
        header_title: Title to display in email header
        body_content: HTML content for email body

    Returns:
        Complete HTML email string
    """
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden;">
                    <!-- Header with Logo -->
                    <tr>
                        <td style="background-color: {UTESCA_BLUE}; padding: 30px; text-align: center;">
                            <img src="{LOGO_URL}" alt="UTESCA Logo" style="max-width: 200px; height: auto; margin-bottom: 15px;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 24px;">{header_title}</h1>
                        </td>
                    </tr>

                    <!-- Body -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            {body_content}
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 20px 30px; text-align: center; border-top: 1px solid #e9ecef;">
                            <p style="margin: 0 0 10px 0; font-size: 14px; color: #666;">
                                Questions? Reply to this email.
                            </p>
                            <p style="margin: 0; font-size: 12px; color: #999;">
                                University of Toronto Engineering Students Consulting Association
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""


def _build_event_details_box(event_title: str, event_datetime: str, event_location: str) -> str:
    """
    Build event details box HTML.

    Args:
        event_title: Event title
        event_datetime: Formatted datetime string
        event_location: Event location

    Returns:
        HTML for event details box
    """
    return f"""
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8f9fa; border-left: 4px solid {UTESCA_BLUE}; margin: 20px 0;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <p style="margin: 0 0 10px 0; font-size: 14px; color: #666;">
                                            <strong style="color: {UTESCA_BLUE};">Event:</strong> {event_title}
                                        </p>
                                        <p style="margin: 0 0 10px 0; font-size: 14px; color: #666;">
                                            <strong style="color: {UTESCA_BLUE};">Date & Time:</strong> {event_datetime}
                                        </p>
                                        <p style="margin: 0; font-size: 14px; color: #666;">
                                            <strong style="color: {UTESCA_BLUE};">Location:</strong> {event_location}
                                        </p>
                                    </td>
                                </tr>
                            </table>
"""


def _build_cta_button(link: str, text: str) -> str:
    """
    Build CTA button HTML.

    Args:
        link: Button URL
        text: Button text

    Returns:
        HTML for CTA button with fallback link
    """
    return f"""
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
                                <tr>
                                    <td align="center">
                                        <a href="{link}" style="display: inline-block; padding: 15px 40px; background-color: {UTESCA_BLUE}; color: #ffffff; text-decoration: none; border-radius: 5px; font-size: 16px; font-weight: bold;">
                                            {text}
                                        </a>
                                    </td>
                                </tr>
                            </table>

                            <p style="font-size: 14px; color: #666666; margin: 20px 0 0 0;">
                                If the button doesn't work, copy and paste this link into your browser:<br>
                                <a href="{link}" style="color: {UTESCA_BLUE}; word-break: break-all;">{link}</a>
                            </p>
"""


def build_confirmation_email(
    full_name: Optional[str],
    event_title: str,
    event_datetime: str,
    event_location: str,
    registration_id: str,
    base_url: str,
) -> Tuple[str, str]:
    """
    Build HTML and plain text email for registration confirmation (auto-accepted).

    Args:
        full_name: User's name (None if not available)
        event_title: Title of the event
        event_datetime: Formatted datetime string (Toronto time)
        event_location: Event location
        registration_id: Registration ID for RSVP link
        base_url: Base URL for RSVP link

    Returns:
        Tuple of (html_body, text_body)
    """
    rsvp_link = f"{base_url}/rsvp/{registration_id}"
    greeting = f"Hi {full_name}," if full_name else "Thank you for registering!"

    # Build HTML body content
    body_content = f"""
                            <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">
                                {greeting}
                            </p>

                            <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">
                                Your registration for <strong>{event_title}</strong> has been received! We're excited to see you there.
                            </p>

                            {_build_event_details_box(event_title, event_datetime, event_location)}

                            <p style="font-size: 16px; color: #333333; margin: 20px 0;">
                                Please confirm your attendance by clicking the button below:
                            </p>

                            {_build_cta_button(rsvp_link, "Confirm Attendance")}
"""

    html_body = _build_email_html("Registration Confirmed!", body_content)

    # Plain text version
    text_body = f"""{greeting}

Your registration for {event_title} has been received! We're excited to see you there.

EVENT DETAILS
-------------
Event: {event_title}
Date & Time: {event_datetime}
Location: {event_location}

CONFIRM YOUR ATTENDANCE
Please confirm your attendance by visiting this link:
{rsvp_link}

---
Questions? Reply to this email.

University of Toronto Engineering Students Consulting Association
"""

    return (html_body, text_body)


def build_application_received_email(
    full_name: Optional[str],
    event_title: str,
    event_datetime: str,
    event_location: str,
) -> Tuple[str, str]:
    """
    Build HTML and plain text email for application received notification (manual review).

    Args:
        full_name: User's name (None if not available)
        event_title: Title of the event
        event_datetime: Formatted datetime string (Toronto time)
        event_location: Event location

    Returns:
        Tuple of (html_body, text_body)
    """
    greeting = f"Hi {full_name}," if full_name else "Thank you for applying!"

    # Build HTML body content
    body_content = f"""
                            <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">
                                {greeting}
                            </p>

                            <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">
                                Thank you for applying to <strong>{event_title}</strong>! We've received your application and our team will review it shortly.
                            </p>

                            {_build_event_details_box(event_title, event_datetime, event_location)}

                            <p style="font-size: 16px; color: #333333; margin: 20px 0;">
                                We'll notify you via email once your application has been reviewed. If accepted, you'll receive a confirmation link to RSVP for the event.
                            </p>

                            <p style="font-size: 16px; color: #333333; margin: 20px 0;">
                                Thank you for your interest in UTESCA!
                            </p>
"""

    html_body = _build_email_html("Application Received", body_content)

    # Plain text version
    text_body = f"""{greeting}

Thank you for applying to {event_title}! We've received your application and our team will review it shortly.

EVENT DETAILS
-------------
Event: {event_title}
Date & Time: {event_datetime}
Location: {event_location}

NEXT STEPS
We'll notify you via email once your application has been reviewed. If accepted, you'll receive a confirmation link to RSVP for the event.

Thank you for your interest in UTESCA!

---
Questions? Reply to this email.

University of Toronto Engineering Students Consulting Association
"""

    return (html_body, text_body)


def build_attendance_confirmed_email(
    full_name: Optional[str],
    event_title: str,
    event_datetime: str,
    event_location: str,
    registration_id: str,
    base_url: str,
) -> Tuple[str, str]:
    """
    Build HTML and plain text email for attendance confirmation.

    Sent when a user confirms their attendance via the RSVP page.

    Args:
        full_name: User's name (None if not available)
        event_title: Title of the event
        event_datetime: Formatted datetime string (Toronto time)
        event_location: Event location
        registration_id: Registration ID for RSVP link
        base_url: Base URL for RSVP link

    Returns:
        Tuple of (html_body, text_body)
    """
    rsvp_link = f"{base_url}/rsvp/{registration_id}"
    greeting = f"Hi {full_name}," if full_name else "Hello!"

    # Build HTML body content
    body_content = f"""
                            <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">
                                {greeting}
                            </p>

                            <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">
                                Great news! You are confirmed for <strong>{event_title}</strong>. We look forward to seeing you there!
                            </p>

                            {_build_event_details_box(event_title, event_datetime, event_location)}

                            <p style="font-size: 16px; color: #333333; margin: 20px 0;">
                                <strong>Unable to make it?</strong> You can change your RSVP response using the link below. Please note that declining is final.
                            </p>

                            {_build_cta_button(rsvp_link, "View RSVP Details")}
"""

    html_body = _build_email_html(f"You're Confirmed for {event_title}!", body_content)

    # Plain text version
    text_body = f"""{greeting}

Great news! You are confirmed for {event_title}. We look forward to seeing you there!

EVENT DETAILS
-------------
Event: {event_title}
Date & Time: {event_datetime}
Location: {event_location}

UNABLE TO MAKE IT?
You can change your RSVP response using this link: {rsvp_link}
Please note that declining is final.

---
Questions? Reply to this email.

University of Toronto Engineering Students Consulting Association
"""

    return (html_body, text_body)


def build_attendance_declined_email(
    full_name: Optional[str],
    event_title: str,
    event_datetime: str,
    event_location: str,
) -> Tuple[str, str]:
    """
    Build HTML and plain text email for attendance decline confirmation.

    Sent when a user declines their attendance (sets status to not_attending).
    This is a final decision and cannot be reversed.

    Args:
        full_name: User's name (None if not available)
        event_title: Title of the event
        event_datetime: Formatted datetime string (Toronto time)
        event_location: Event location

    Returns:
        Tuple of (html_body, text_body)
    """
    greeting = f"Hi {full_name}," if full_name else "Hello,"

    # Build HTML body content
    body_content = f"""
                            <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">
                                {greeting}
                            </p>

                            <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">
                                You are no longer attending <strong>{event_title}</strong>. We have received your RSVP response.
                            </p>

                            {_build_event_details_box(event_title, event_datetime, event_location)}

                            <!-- Important Notice Box -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #fff3cd; border-left: 4px solid #856404; margin: 20px 0;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <p style="margin: 0; font-size: 14px; color: #856404;">
                                            <strong>Please note:</strong> This change is final and cannot be reversed. If you change your mind, please reply to this email.
                                        </p>
                                    </td>
                                </tr>
                            </table>

                            <p style="font-size: 16px; color: #333333; margin: 20px 0;">
                                We hope to see you at future UTESCA events!
                            </p>
"""

    html_body = _build_email_html("RSVP Response Received", body_content)

    # Plain text version
    text_body = f"""{greeting}

You are no longer attending {event_title}. We have received your RSVP response.

EVENT DETAILS
-------------
Event: {event_title}
Date & Time: {event_datetime}
Location: {event_location}

IMPORTANT
This change is final and cannot be reversed. If you change your mind, please reply to this email.

We hope to see you at future UTESCA events!

---
Questions? Reply to this email.

University of Toronto Engineering Students Consulting Association
"""

    return (html_body, text_body)

def build_password_reset_email(
    token: str,
    base_url: str,
    full_name: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Build HTML and plain text email for password reset request.

    Args:
        token: The unique UUID reset token
        base_url: The base portal URL (e.g., portal.utesca.ca)
        full_name: User's name (None if not available)

    Returns:
        Tuple of (html_body, text_body)
    """
    reset_link = f"{base_url}/reset-password?token={token}"
    greeting = f"Hi {full_name}," if full_name else "Hello,"

    # Build HTML body content
    body_content = f"""
                            <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">
                                {greeting}
                            </p>

                            <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">
                                We received a request to reset your password for your UTESCA account. Click the button below to choose a new password:
                            </p>

                            <table width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
                                <tr>
                                    <td align="center">
                                        <a href="{reset_link}" style="background-color: #007bff; color: #ffffff; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                                            Reset Password
                                        </a>
                                    </td>
                                </tr>
                            </table>

                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8f9fa; border-left: 4px solid #6c757d; margin: 20px 0;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <p style="margin: 0; font-size: 14px; color: #495057;">
                                            <strong>Safety first:</strong> This link will expire in <strong>1 hour</strong>. If you did not request this change, you can safely ignore this email.
                                        </p>
                                    </td>
                                </tr>
                            </table>

                            <p style="font-size: 14px; color: #777777; margin: 20px 0;">
                                If the button above doesn't work, copy and paste this URL into your browser:<br>
                                <a href="{reset_link}" style="color: #007bff;">{reset_link}</a>
                            </p>
                    """

    html_body = _build_email_html("Password Reset Request", body_content)

    # Plain text version
    text_body = f"""{greeting}

    We received a request to reset your password for your UTESCA account.

    Click the link below to choose a new password. This link will expire in 1 hour.

    {reset_link}

    If you did not request this change, you can safely ignore this email.

    ---
    Questions? Reply to this email.

    University of Toronto Engineering Students Consulting Association
    """

    return (html_body, text_body)


