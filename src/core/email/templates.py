"""
Email template builders for various email types.
Returns both HTML and plain text versions for better email client compatibility.
"""

from typing import Tuple
from core.config import get_settings

# Load configuration
_settings = get_settings()
LOGO_URL = _settings.EMAIL_LOGO_URL if hasattr(_settings, 'EMAIL_LOGO_URL') else ""

# Brand colors
UTESCA_BLUE = "#121921"


def _build_email_html(header_title: str, body_content: str) -> str:
    """Build HTML email wrapper with header and footer."""
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: {UTESCA_BLUE}; color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
            .header h1 {{ margin: 0; font-size: 24px; }}
            .content {{ background-color: #f9f9f9; padding: 30px; border-bottom: 1px solid #e0e0e0; }}
            .footer {{ background-color: #f0f0f0; padding: 20px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 8px 8px; }}
            .footer p {{ margin: 5px 0; }}
            .cta-button {{ display: inline-block; background-color: {UTESCA_BLUE}; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            table {{ width: 100%; border-collapse: collapse; }}
            td {{ padding: 8px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{header_title}</h1>
            </div>
            <div class="content">
                {body_content}
            </div>
            <div class="footer">
                <p>University of Toronto Engineering Students Consulting Association</p>
                <p>© 2025 UTESCA. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_template


def build_announcement_email(
    full_name: str | None,
    announcement_title: str,
    announcement_content: str,
    priority: str,
) -> Tuple[str, str]:
    """
    Build HTML and plain text email for announcements.

    Args:
        full_name: Recipient's name (None if not available)
        announcement_title: Announcement title
        announcement_content: Announcement content/message
        priority: Announcement priority ('normal' or 'urgent')

    Returns:
        Tuple of (html_body, text_body)
    """
    greeting = f"Hi {full_name}," if full_name else "Hello,"
    priority_badge = "[URGENT] " if priority == "urgent" else ""

    # HTML version
    body_content = f"""
                            <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">
                                {greeting}
                            </p>

                            <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">
                                {announcement_content}
                            </p>
    """

    if priority == "urgent":
        body_content = f"""
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #fff3cd; border-left: 4px solid #856404; margin: 20px 0;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <p style="margin: 0 0 10px 0; font-size: 14px; font-weight: bold; color: #856404;">
                                            ⚠️ URGENT ANNOUNCEMENT
                                        </p>
                                        <p style="margin: 0; font-size: 14px; color: #856404;">
                                            This is an urgent announcement. Please read carefully.
                                        </p>
                                    </td>
                                </tr>
                            </table>

                            <p style="font-size: 16px; color: #333333; margin: 20px 0 20px 0;">
                                {greeting}
                            </p>

                            <p style="font-size: 16px; color: #333333; margin: 0 0 20px 0;">
                                {announcement_content}
                            </p>
        """

    html_body = _build_email_html(priority_badge + announcement_title, body_content)

    # Plain text version
    text_body = f"""{greeting}

{announcement_content}

---
University of Toronto Engineering Students Consulting Association
"""

    return (html_body, text_body)
