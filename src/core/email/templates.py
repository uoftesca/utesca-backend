"""
Email template builders for various email types.
Returns both HTML and plain text versions for better email client compatibility.
"""

from typing import Tuple, Optional

# UTESCA logo URL
LOGO_URL = "https://raw.githubusercontent.com/uoftesca/utesca-frontend/main/public/UTESCA-red-black.png?raw=true"

# Brand colors
UTESCA_BLUE = "#121921"


def build_confirmation_email(
    full_name: Optional[str],
    event_title: str,
    event_datetime: str,
    event_location: str,
    rsvp_token: str,
    base_url: str,
) -> Tuple[str, str]:
    """
    Build HTML and plain text email for registration confirmation (auto-accepted).

    Args:
        full_name: User's name (None if not available)
        event_title: Title of the event
        event_datetime: Formatted datetime string (Toronto time)
        event_location: Event location
        rsvp_token: RSVP confirmation token
        base_url: Base URL for RSVP link

    Returns:
        Tuple of (html_body, text_body)
    """
    rsvp_link = f"{base_url}/rsvp/{rsvp_token}"

    # Greeting based on whether name is available
    greeting = f"Hi {full_name}," if full_name else "Thank you for registering!"

    # HTML version
    html_body = f"""
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
                            <h1 style="color: #ffffff; margin: 0; font-size: 24px;">Registration Confirmed!</h1>
                        </td>
                    </tr>

                    <!-- Body -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">
                                {greeting}
                            </p>

                            <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">
                                Your registration for <strong>{event_title}</strong> has been confirmed! We're excited to see you there.
                            </p>

                            <!-- Event Details Box -->
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

                            <p style="font-size: 16px; color: #333333; margin: 20px 0;">
                                Please confirm your attendance by clicking the button below:
                            </p>

                            <!-- CTA Button -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
                                <tr>
                                    <td align="center">
                                        <a href="{rsvp_link}" style="display: inline-block; padding: 15px 40px; background-color: {UTESCA_BLUE}; color: #ffffff; text-decoration: none; border-radius: 5px; font-size: 16px; font-weight: bold;">
                                            Confirm Attendance
                                        </a>
                                    </td>
                                </tr>
                            </table>

                            <p style="font-size: 14px; color: #666666; margin: 20px 0 0 0;">
                                If the button doesn't work, copy and paste this link into your browser:<br>
                                <a href="{rsvp_link}" style="color: {UTESCA_BLUE}; word-break: break-all;">{rsvp_link}</a>
                            </p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 20px 30px; text-align: center; border-top: 1px solid #e9ecef;">
                            <p style="margin: 0 0 10px 0; font-size: 14px; color: #666;">
                                Questions? Contact us at <a href="mailto:uoft.esca@gmail.com" style="color: {UTESCA_BLUE};">uoft.esca@gmail.com</a>
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

    # Plain text version
    text_body = f"""{greeting}

Your registration for {event_title} has been confirmed! We're excited to see you there.

EVENT DETAILS
-------------
Event: {event_title}
Date & Time: {event_datetime}
Location: {event_location}

CONFIRM YOUR ATTENDANCE
Please confirm your attendance by visiting this link:
{rsvp_link}

---
Questions? Contact us at uoft.esca@gmail.com

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
    # Greeting based on whether name is available
    greeting = f"Hi {full_name}," if full_name else "Thank you for applying!"

    # HTML version
    html_body = f"""
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
                            <h1 style="color: #ffffff; margin: 0; font-size: 24px;">Application Received</h1>
                        </td>
                    </tr>

                    <!-- Body -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">
                                {greeting}
                            </p>

                            <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">
                                Thank you for applying to <strong>{event_title}</strong>! We've received your application and our team will review it shortly.
                            </p>

                            <!-- Event Details Box -->
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

                            <p style="font-size: 16px; color: #333333; margin: 20px 0;">
                                We'll notify you via email once your application has been reviewed. If accepted, you'll receive a confirmation link to RSVP for the event.
                            </p>

                            <p style="font-size: 16px; color: #333333; margin: 20px 0;">
                                Thank you for your interest in UTESCA!
                            </p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 20px 30px; text-align: center; border-top: 1px solid #e9ecef;">
                            <p style="margin: 0 0 10px 0; font-size: 14px; color: #666;">
                                Questions? Contact us at <a href="mailto:uoft.esca@gmail.com" style="color: {UTESCA_BLUE};">uoft.esca@gmail.com</a>
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
Questions? Contact us at uoft.esca@gmail.com

University of Toronto Engineering Students Consulting Association
"""

    return (html_body, text_body)
