"""Public links and QR payloads used by the registration flow."""

import json
from urllib.parse import urlencode
from uuid import UUID


def _build_token_url(base_url: str, registration_id: UUID, action: str, token: str) -> str:
    query = urlencode({"token": token})
    return f"{base_url.rstrip('/')}/registrations/{registration_id}/{action}?{query}"


def build_verification_url(base_url: str, registration_id: UUID, token: str) -> str:
    return _build_token_url(base_url, registration_id, "verify", token)


def build_management_url(base_url: str, registration_id: UUID, token: str) -> str:
    return _build_token_url(base_url, registration_id, "manage", token)


def build_rsvp_url(base_url: str, registration_id: UUID, token: str) -> str:
    return _build_token_url(base_url, registration_id, "rsvp", token)


def build_ticket_qr_payload(registration_id: UUID, ticket_token: str) -> str:
    """Build a versioned payload for the staff check-in scanner."""
    return json.dumps(
        {"v": 1, "registrationId": str(registration_id), "ticketToken": ticket_token},
        separators=(",", ":"),
    )
