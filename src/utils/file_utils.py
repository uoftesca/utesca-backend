"""
Pure utility functions for ZIP file download filename generation.

No I/O, no service dependencies. All functions operate on plain data.
"""

import unicodedata
from typing import Any, Dict, Set, Tuple
from uuid import UUID


def sanitize_filename(name: str) -> str:
    """Strip or transliterate accented/special characters to ASCII-safe equivalents.

    Normalizes via NFKD decomposition, encodes to ASCII (dropping combining marks),
    then removes anything that is not alphanumeric, a hyphen, or a dot. Consecutive
    hyphens are collapsed to one, and leading/trailing hyphens are stripped from each
    dot-separated segment.
    """
    normalized = unicodedata.normalize("NFKD", name)
    ascii_bytes = normalized.encode("ascii", errors="ignore")
    ascii_str = ascii_bytes.decode("ascii")

    # Keep only alphanumeric, hyphen, dot
    filtered = "".join(ch if ch.isalnum() or ch in ("-", ".") else "-" for ch in ascii_str)

    # Collapse consecutive hyphens
    while "--" in filtered:
        filtered = filtered.replace("--", "-")

    # Strip leading/trailing hyphens from each dot-separated segment
    segments = [seg.strip("-") for seg in filtered.split(".")]
    return ".".join(seg for seg in segments if seg)


def extract_name_parts(form_data: Dict[str, Any]) -> Tuple[str, str]:
    """Extract first and last name separately from form_data.

    Tries in order:
        1. firstName / lastName (camelCase)
        2. first_name / last_name (snake_case)
        3. fullName or full_name — splits on whitespace: first token = first name,
           last token = last name.

    Returns:
        Tuple of (first_name, last_name). Returns ("", "") if no name fields found.
    """
    first = str(form_data.get("firstName", "")).strip()
    last = str(form_data.get("lastName", "")).strip()
    if first or last:
        return first, last

    first = str(form_data.get("first_name", "")).strip()
    last = str(form_data.get("last_name", "")).strip()
    if first or last:
        return first, last

    full = str(form_data.get("fullName", "") or form_data.get("full_name", "")).strip()
    if full:
        parts = full.split()
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], parts[-1]

    return "", ""


def generate_zip_filename(
    field_name: str,
    form_data: Dict[str, Any],
    original_filename: str,
    registration_id: UUID,
) -> str:
    """Generate a deterministic filename for a file inside the ZIP archive.

    Format: ``{last}-{first}-{field_name}.{ext}``
    Falls back to ``{registration_id}-{field_name}.{ext}`` when both name parts
    are empty after sanitization.

    The extension is extracted from *original_filename*; if none is present the
    file is written without one.
    """
    first, last = extract_name_parts(form_data)
    sanitized_first = sanitize_filename(first)
    sanitized_last = sanitize_filename(last)
    sanitized_field = sanitize_filename(field_name)

    # Split extension from original filename
    if "." in original_filename:
        ext = original_filename.rsplit(".", 1)[1]
    else:
        ext = ""

    if sanitized_last or sanitized_first:
        base = f"{sanitized_last}-{sanitized_first}-{sanitized_field}"
    else:
        base = f"{registration_id}-{sanitized_field}"

    result = f"{base}.{ext}" if ext else base
    return result.lower()


def deduplicate_filename(filename: str, used_names: Set[str]) -> str:
    """Return a unique variant of *filename* that is not already in *used_names*.

    If *filename* is already taken, appends ``-2``, ``-3``, etc. before the
    extension until a unique name is found.
    """
    if filename not in used_names:
        return filename

    if "." in filename:
        stem, ext = filename.rsplit(".", 1)
        counter = 2
        while f"{stem}-{counter}.{ext}" in used_names:
            counter += 1
        return f"{stem}-{counter}.{ext}"

    counter = 2
    while f"{filename}-{counter}" in used_names:
        counter += 1
    return f"{filename}-{counter}"
