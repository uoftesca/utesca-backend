import json
from uuid import UUID

from core.email.templates import (
    build_application_accepted_email,
    build_application_received_email,
    build_e_ticket_email,
    build_identity_verification_email,
)
from domains.events.registrations.links import (
    build_management_url,
    build_rsvp_url,
    build_ticket_qr_payload,
    build_verification_url,
)

REGISTRATION_ID = UUID("4fe1e2a3-2223-4e30-a52b-6e01e8be08d2")
BASE_URL = "https://utesca.ca/"


def test_registration_token_links_use_registration_route_and_raw_token() -> None:
    token = "opaque token/+"

    assert build_verification_url(BASE_URL, REGISTRATION_ID, token) == (
        f"https://utesca.ca/registrations/{REGISTRATION_ID}/verify?token=opaque+token%2F%2B"
    )
    assert build_management_url(BASE_URL, REGISTRATION_ID, token) == (
        f"https://utesca.ca/registrations/{REGISTRATION_ID}/manage?token=opaque+token%2F%2B"
    )
    assert build_rsvp_url(BASE_URL, REGISTRATION_ID, token) == (
        f"https://utesca.ca/registrations/{REGISTRATION_ID}/rsvp?token=opaque+token%2F%2B"
    )


def test_ticket_qr_payload_contains_version_registration_and_token() -> None:
    payload = json.loads(build_ticket_qr_payload(REGISTRATION_ID, "ticket-token"))

    assert payload == {
        "v": 1,
        "registrationId": str(REGISTRATION_ID),
        "ticketToken": "ticket-token",
    }


def test_registration_email_templates_include_required_actions() -> None:
    verification_url = build_verification_url(BASE_URL, REGISTRATION_ID, "verification-token")
    management_url = build_management_url(BASE_URL, REGISTRATION_ID, "management-token")

    verification_html, verification_text = build_identity_verification_email(
        full_name="Alex",
        event_title="Consulting Night",
        verification_url=verification_url,
        verification_deadline="September 25, 2026 at 11:59 PM ET",
    )
    application_html, application_text = build_application_received_email(
        full_name="Alex",
        event_title="Consulting Night",
        event_datetime="October 2, 2026 at 6:00 PM ET",
        event_location="Myhal Centre",
        management_url=management_url,
    )
    ticket_html, ticket_text = build_e_ticket_email(
        full_name="Alex",
        event_title="Consulting Night",
        event_datetime="October 2, 2026 at 6:00 PM ET",
        event_location="Myhal Centre",
        management_url=management_url,
    )
    rsvp_html, rsvp_text = build_application_accepted_email(
        full_name="Alex",
        event_title="Consulting Night",
        event_datetime="October 2, 2026 at 6:00 PM ET",
        event_location="Myhal Centre",
        registration_id=str(REGISTRATION_ID),
        base_url=BASE_URL,
        rsvp_url=build_rsvp_url(BASE_URL, REGISTRATION_ID, "rsvp-token"),
        rsvp_deadline="September 29, 2026 at 11:59 PM ET",
    )

    assert verification_url in verification_html and verification_url in verification_text
    assert "September 25, 2026" in verification_html
    assert management_url in application_html and management_url in application_text
    assert 'src="cid:ticket-qr"' in ticket_html
    assert management_url in ticket_html and management_url in ticket_text
    assert "rsvp-token" in rsvp_html and "rsvp-token" in rsvp_text
    assert "September 29, 2026" in rsvp_html and "September 29, 2026" in rsvp_text
