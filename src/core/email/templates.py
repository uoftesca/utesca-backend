"""
Email template builders for various email types.
Returns both HTML and plain text versions for better email client compatibility.
"""

from typing import Dict, Literal, Optional, Tuple

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


def build_rsvp_decline_notification(
    attendee_name: Optional[str],
    attendee_email: str,
    event_title: str,
    event_datetime: str,
    event_location: str,
    previous_status: str,
) -> Tuple[str, str]:
    """
    Build HTML and plain text email for RSVP decline notification.

    Sent to subscribed users when an attendee declines confirmed attendance.
    This is an internal notification for event organizers and interested team members.

    Args:
        attendee_name: Attendee's name (None if not available)
        attendee_email: Attendee's email address
        event_title: Title of the event
        event_datetime: Formatted datetime string (Toronto time)
        event_location: Event location
        previous_status: Status before decline (should be "confirmed")

    Returns:
        Tuple of (html_body, text_body)
    """
    # Use name if available, otherwise use email
    attendee_display = attendee_name if attendee_name else attendee_email

    # HTML version
    body_content = f"""
                            <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">
                                An attendee has declined their confirmed attendance for <strong>{event_title}</strong>.
                            </p>

                            <!-- Attendee Information Box (Warning Style) -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #fff3cd; border-left: 4px solid #856404; margin: 20px 0;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <p style="margin: 0 0 10px 0; font-size: 14px; color: #856404;">
                                            <strong>Attendee:</strong> {attendee_display}
                                        </p>
                                        <p style="margin: 0 0 10px 0; font-size: 14px; color: #856404;">
                                            <strong>Email:</strong> {attendee_email}
                                        </p>
                                        <p style="margin: 0; font-size: 14px; color: #856404;">
                                            <strong>Previous Status:</strong> {previous_status}
                                        </p>
                                    </td>
                                </tr>
                            </table>

                            {_build_event_details_box(event_title, event_datetime, event_location)}

                            <p style="font-size: 14px; color: #666666; margin: 20px 0;">
                                You received this notification because you have RSVP change notifications enabled in your preferences.
                            </p>
"""

    html_body = _build_email_html("RSVP Decline Notification", body_content)

    # Plain text version
    text_body = f"""An attendee has declined their confirmed attendance for {event_title}.

ATTENDEE INFORMATION
--------------------
Attendee: {attendee_display}
Email: {attendee_email}
Previous Status: {previous_status}

EVENT DETAILS
-------------
Event: {event_title}
Date & Time: {event_datetime}
Location: {event_location}

You received this notification because you have RSVP change notifications enabled in your preferences.

---
Questions? Reply to this email.

University of Toronto Engineering Students Consulting Association
"""

    return (html_body, text_body)


def _replace_template_variables(template: str, variables: Dict[str, str]) -> str:
    """
    Replace template variables in format {{variable_name}} with actual values.

    Args:
        template: Template string with {{variable}} placeholders
        variables: Dictionary of variable names to replacement values

    Returns:
        String with variables replaced

    Example:
        >>> _replace_template_variables(
        ...     "Hi {{full_name}}, welcome to {{event_title}}!",
        ...     {"full_name": "John Doe", "event_title": "Tech Talk"}
        ... )
        'Hi John Doe, welcome to Tech Talk!'
    """
    result = template
    for key, value in variables.items():
        placeholder = f"{{{{{key}}}}}"  # Creates {{key}}
        result = result.replace(placeholder, str(value))
    return result


def build_application_accepted_email(
    full_name: Optional[str],
    event_title: str,
    event_datetime: str,
    event_location: str,
    registration_id: str,
    base_url: str,
) -> Tuple[str, str]:
    """
    Build HTML and plain text email for application acceptance.

    Sent when VP/Admin accepts a submitted application via portal.
    Includes RSVP link for attendee to confirm attendance.

    Args:
        full_name: Applicant's name (None if not available)
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

    # HTML version
    body_content = f"""
                            <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">
                                {greeting}
                            </p>

                            <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">
                                Great news! Your application for <strong>{event_title}</strong> has been accepted. We're excited to have you join us!
                            </p>

                            {_build_event_details_box(event_title, event_datetime, event_location)}

                            <p style="font-size: 16px; color: #333333; margin: 20px 0;">
                                Please confirm your attendance by clicking the button below:
                            </p>

                            {_build_cta_button(rsvp_link, "Confirm Attendance")}
"""

    html_body = _build_email_html("Application Accepted!", body_content)

    # Plain text version
    text_body = f"""{greeting}

Great news! Your application for {event_title} has been accepted. We're excited to have you join us!

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


def build_application_rejected_email(
    full_name: Optional[str],
    event_title: str,
    event_datetime: str,
    event_location: str,
) -> Tuple[str, str]:
    """
    Build HTML and plain text email for application rejection.

    Sent when VP/Admin rejects a submitted application via portal.

    Args:
        full_name: Applicant's name (None if not available)
        event_title: Title of the event
        event_datetime: Formatted datetime string (Toronto time)
        event_location: Event location

    Returns:
        Tuple of (html_body, text_body)
    """
    greeting = f"Hi {full_name}," if full_name else "Hello,"

    # HTML version
    body_content = f"""
                            <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">
                                {greeting}
                            </p>

                            <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">
                                Thank you for your interest in <strong>{event_title}</strong>. Unfortunately, we are unable to accept your application at this time due to capacity constraints.
                            </p>

                            {_build_event_details_box(event_title, event_datetime, event_location)}

                            <p style="font-size: 16px; color: #333333; margin: 20px 0;">
                                We encourage you to apply for future UTESCA events and appreciate your continued interest in our community.
                            </p>

                            <p style="font-size: 16px; color: #333333; margin: 20px 0;">
                                Thank you for your time.
                            </p>
"""

    html_body = _build_email_html("Application Status Update", body_content)

    # Plain text version
    text_body = f"""{greeting}

Thank you for your interest in {event_title}. Unfortunately, we are unable to accept your application at this time due to capacity constraints.

EVENT DETAILS
-------------
Event: {event_title}
Date & Time: {event_datetime}
Location: {event_location}

We encourage you to apply for future UTESCA events and appreciate your continued interest in our community.

Thank you for understanding.

---
Questions? Reply to this email.

University of Toronto Engineering Students Consulting Association
"""

    return (html_body, text_body)


def build_custom_email_from_template(
    template_subject: str,
    template_body: str,
    full_name: Optional[str],
    event_title: str,
    event_datetime: str,
    event_location: str,
    registration_id: str,
    base_url: str,
    email_type: Literal["acceptance", "rejection"],
) -> Tuple[str, str]:
    """
    Build email from custom template with variable replacement.

    Supports template variables:
    - {{full_name}}: Recipient's name
    - {{event_title}}: Event title
    - {{event_datetime}}: Formatted event date/time
    - {{event_location}}: Event location
    - {{rsvp_link}}: RSVP confirmation link (acceptance emails only)

    Args:
        template_subject: Custom email subject with variables
        template_body: Custom email body with variables
        full_name: Recipient's name (None if not available)
        event_title: Event title
        event_datetime: Formatted datetime string (Toronto time)
        event_location: Event location
        registration_id: Registration ID for RSVP link
        base_url: Base URL for RSVP link
        email_type: "acceptance" or "rejection" (determines if RSVP link included)

    Returns:
        Tuple of (html_body, text_body)
    """
    rsvp_link = f"{base_url}/rsvp/{registration_id}"

    # Build variable replacement dictionary
    variables = {
        "full_name": full_name or "there",
        "event_title": event_title,
        "event_datetime": event_datetime,
        "event_location": event_location,
    }

    # Add RSVP link only for acceptance emails
    if email_type == "acceptance":
        variables["rsvp_link"] = rsvp_link

    # Replace variables in subject and body
    subject = _replace_template_variables(template_subject, variables)
    body_text = _replace_template_variables(template_body, variables)

    # Convert plain text body to HTML (preserve line breaks)
    # Use simple paragraph wrapping
    body_html_paragraphs = []
    for paragraph in body_text.split("\n\n"):
        paragraph = paragraph.strip()
        if paragraph:
            # Convert single newlines to <br>, wrap in <p>
            paragraph_html = paragraph.replace("\n", "<br>")
            body_html_paragraphs.append(
                f'<p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">{paragraph_html}</p>'
            )

    body_content = "\n\n".join(body_html_paragraphs)

    # Add RSVP button for acceptance emails
    if email_type == "acceptance":
        body_content += f"\n\n{_build_cta_button(rsvp_link, 'Confirm Attendance')}"

    html_body = _build_email_html(subject, body_content)

    return (html_body, body_text)
