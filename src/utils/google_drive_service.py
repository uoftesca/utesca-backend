"""
Google Drive utility service - Business logic for Google Drive operations.

This module handles generating direct download links from Google Drive URLs.
"""

import re
from typing import Optional

from .google_drive_models import GoogleDriveDirectLinkResponse


def _extract_file_id(url: str) -> Optional[str]:
    """
    Extract file ID from various Google Drive URL formats.

    This is a private helper function used internally by generate_direct_link().

    Supported formats:
    - https://drive.google.com/file/d/{fileId}/view?usp=sharing
    - https://drive.google.com/file/d/{fileId}/view
    - https://drive.google.com/open?id={fileId}
    - https://drive.google.com/drive/u/1/folders/{fileId}
    - https://drive.google.com/drive/folders/{fileId}
    - And various other Google Drive URL patterns

    Args:
        url: Google Drive URL

    Returns:
        File ID if found, None otherwise
    """
    if not url or not isinstance(url, str):
        return None

    # Pattern 1: /file/d/{fileId}/
    pattern1 = r"/file/d/([a-zA-Z0-9_-]+)"
    match = re.search(pattern1, url)
    if match:
        return match.group(1)

    # Pattern 2: /folders/{fileId}
    pattern2 = r"/folders/([a-zA-Z0-9_-]+)"
    match = re.search(pattern2, url)
    if match:
        return match.group(1)

    # Pattern 3: ?id={fileId} or &id={fileId}
    pattern3 = r"[?&]id=([a-zA-Z0-9_-]+)"
    match = re.search(pattern3, url)
    if match:
        return match.group(1)

    # Pattern 4: /d/{fileId}/ (more general pattern)
    pattern4 = r"/d/([a-zA-Z0-9_-]+)"
    match = re.search(pattern4, url)
    if match:
        return match.group(1)

    return None


def generate_direct_link(url: str) -> GoogleDriveDirectLinkResponse:
    """
    Generate a direct download link from a Google Drive URL.

    This function extracts the file ID from various Google Drive URL formats
    and generates a direct download link that immediately starts downloading
    the file rather than opening a preview.

    Args:
        url: Google Drive URL (various formats supported)

    Returns:
        GoogleDriveDirectLinkResponse with original_url, direct_url, and optional error

    Example:
        >>> result = generate_direct_link("https://drive.google.com/file/d/1Ggj.../view?usp=sharing")
        >>> print(result.direct_url)
        "https://drive.google.com/uc?export=download&id=1Ggj..."
    """
    # Validate input
    if not url or not isinstance(url, str):
        return GoogleDriveDirectLinkResponse(
            original_url=url or "", direct_url=None, error="Invalid URL: URL must be a non-empty string"
        )

    url = url.strip()

    # Check if it's a Google Drive URL
    if "drive.google.com" not in url:
        return GoogleDriveDirectLinkResponse(
            original_url=url, direct_url=None, error="Invalid URL: Not a Google Drive URL"
        )

    # Extract file ID
    file_id = _extract_file_id(url)

    if not file_id:
        return GoogleDriveDirectLinkResponse(
            original_url=url, direct_url=None, error="Invalid URL: Could not extract file ID from Google Drive URL"
        )

    # Generate direct download link
    direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"

    return GoogleDriveDirectLinkResponse(original_url=url, direct_url=direct_url, error=None)
