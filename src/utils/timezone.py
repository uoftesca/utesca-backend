"""
Timezone conversion utilities for formatting datetimes to Toronto timezone.
"""

from datetime import datetime
from typing import Optional

import pytz


def format_datetime_toronto(dt: datetime, format_str: Optional[str] = None) -> str:
    """
    Convert a datetime to Toronto timezone and format it.

    Args:
        dt: Datetime object (can be naive or timezone-aware)
        format_str: Optional custom format string.
                   Defaults to: "Wednesday, January 15, 2025 at 6:00 PM EST"

    Returns:
        Formatted datetime string in Toronto timezone

    Examples:
        >>> from datetime import datetime, timezone
        >>> dt = datetime(2025, 1, 15, 23, 0, 0, tzinfo=timezone.utc)
        >>> format_datetime_toronto(dt)
        'Wednesday, January 15, 2025 at 6:00 PM EST'
    """
    toronto_tz = pytz.timezone("America/Toronto")

    # If datetime is naive, assume UTC
    if dt.tzinfo is None:
        utc_dt = pytz.utc.localize(dt)
    else:
        utc_dt = dt

    # Convert to Toronto timezone
    toronto_dt = utc_dt.astimezone(toronto_tz)

    # Default format: "Wednesday, January 15, 2025 at 6:00 PM EST"
    if format_str is None:
        format_str = "%A, %B %d, %Y at %-I:%M %p %Z"

    return toronto_dt.strftime(format_str)
