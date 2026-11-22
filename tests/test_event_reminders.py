"""Behavior tests for confirmed-registration event reminders."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from core.email import templates
from domains.events.registrations.service import RegistrationService


@pytest.fixture
def service():
    instance = RegistrationService.__new__(RegistrationService)
    instance.events_repo = Mock()
    instance.reg_repo = Mock()
    return instance


def test_prepare_event_reminder_uses_unique_confirmed_registration_emails(service):
    event_id = uuid4()
    event = Mock(id=event_id, title="UTESCA x Isaac: The Founder’s Test")
    service.events_repo.get_by_id.return_value = event
    service.reg_repo.list_emails_by_status.return_value = [
        " Leena@example.com ",
        "leena@EXAMPLE.com",
        "sundari@example.com",
        None,
        " ",
    ]

    prepared_event, recipients = service.prepare_event_reminder(event_id)

    assert prepared_event is event
    assert recipients == ["Leena@example.com", "sundari@example.com"]
    service.reg_repo.list_emails_by_status.assert_called_once_with(event_id, "confirmed")


def test_prepare_event_reminder_rejects_event_without_confirmed_email_recipients(service):
    service.events_repo.get_by_id.return_value = Mock()
    service.reg_repo.list_emails_by_status.return_value = [None, " "]

    with pytest.raises(HTTPException) as exc_info:
        service.prepare_event_reminder(uuid4())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "No confirmed registrants with email addresses found"


def test_send_event_reminders_uses_event_details_for_each_recipient(service):
    event = Mock(
        title="UTESCA x Isaac: The Founder’s Test",
        date_time=datetime(2026, 10, 6, 22, 0, tzinfo=timezone.utc),
        location="SF1101",
    )

    with patch("domains.events.registrations.service.EmailService") as email_service_class:
        service.send_event_reminders(event, ["one@example.com", "two@example.com"])

    email_service_class.return_value.send_event_reminder.assert_any_call(
        to="one@example.com",
        event_title="UTESCA x Isaac: The Founder’s Test",
        event_datetime="Tuesday, October 06, 2026 at 6:00 PM EDT",
        event_location="SF1101",
        custom_body=None,
    )
    email_service_class.return_value.send_event_reminder.assert_any_call(
        to="two@example.com",
        event_title="UTESCA x Isaac: The Founder’s Test",
        event_datetime="Tuesday, October 06, 2026 at 6:00 PM EDT",
        event_location="SF1101",
        custom_body=None,
    )


def test_send_event_reminders_passes_custom_body_to_each_recipient(service):
    event = Mock(
        title="Case Night",
        date_time=datetime(2026, 10, 6, 22, 0, tzinfo=timezone.utc),
        location=None,
    )

    with patch("domains.events.registrations.service.EmailService") as email_service_class:
        service.send_event_reminders(event, ["one@example.com", "two@example.com"], "See you soon!")

    calls = email_service_class.return_value.send_event_reminder.call_args_list
    assert len(calls) == 2
    assert all(call.kwargs["custom_body"] == "See you soon!" for call in calls)
    assert all(call.kwargs["event_location"] == "TBA" for call in calls)


def test_event_reminder_template_uses_custom_body_escaped_with_bold_markers():
    custom_body = "Hi <all> & friends,\n\n**Event:** Case Night\nBring a laptop."

    html_body, text_body = templates.build_event_reminder_email(
        event_title="Ignored Title",
        event_datetime="Tuesday, October 06, 2026 at 6:00 PM EDT",
        event_location="SF1101",
        custom_body=custom_body,
    )

    assert text_body == custom_body
    assert "Reminder" in html_body
    assert "Hi &lt;all&gt; &amp; friends," in html_body
    assert "<strong>Event:</strong> Case Night" in html_body
    assert "white-space: pre-wrap" in html_body
    assert "Ignored Title" not in html_body
    assert "<all>" not in html_body


def test_send_event_reminder_keeps_subject_with_custom_body():
    from core.email.service import EmailService

    email_service = EmailService.__new__(EmailService)
    with patch.object(EmailService, "send_email", return_value=True) as send_email:
        email_service.send_event_reminder(
            to="one@example.com",
            event_title="Case Night",
            event_datetime="Tuesday, October 06, 2026 at 6:00 PM EDT",
            event_location="SF1101",
            custom_body="Custom text",
        )

    send_email.assert_called_once()
    assert send_email.call_args.kwargs["subject"] == "Reminder"
    assert send_email.call_args.kwargs["text_body"] == "Custom text"


@pytest.fixture
def notify_client():
    import inspect

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from domains.auth.dependencies import get_current_vp_or_admin
    from domains.events.registrations import portal_api

    route = next(r for r in portal_api.router.routes if r.path == "/events/{event_id}/registrations/notify")
    rate_limit_dependency = inspect.signature(route.endpoint).parameters["_rl"].default.dependency

    mock_service = Mock()
    mock_service.prepare_event_reminder.return_value = (Mock(), ["one@example.com", "two@example.com"])

    app = FastAPI()
    app.include_router(portal_api.router, prefix="/portal")
    app.dependency_overrides[rate_limit_dependency] = lambda: None
    app.dependency_overrides[get_current_vp_or_admin] = lambda: Mock()
    app.dependency_overrides[portal_api.get_registration_service] = lambda: mock_service
    return TestClient(app), mock_service


@pytest.mark.parametrize(
    "request_kwargs",
    [{}, {"json": {}}, {"json": {"body": None}}, {"json": {"body": "   \n "}}],
    ids=["no-body", "empty-object", "null-body", "blank-body"],
)
def test_notify_endpoint_sends_default_reminder_without_custom_body(notify_client, request_kwargs):
    client, mock_service = notify_client
    event_id = uuid4()

    response = client.post(f"/portal/events/{event_id}/registrations/notify", **request_kwargs)

    assert response.status_code == 202
    assert response.json() == {"success": True, "queued": 2}
    event, recipients = mock_service.prepare_event_reminder.return_value
    mock_service.send_event_reminders.assert_called_once_with(event, recipients, None)


def test_notify_endpoint_forwards_custom_body(notify_client):
    client, mock_service = notify_client

    response = client.post(
        f"/portal/events/{uuid4()}/registrations/notify",
        json={"body": "Hi all,\nsee you Friday!"},
    )

    assert response.status_code == 202
    event, recipients = mock_service.prepare_event_reminder.return_value
    mock_service.send_event_reminders.assert_called_once_with(event, recipients, "Hi all,\nsee you Friday!")


def test_notify_endpoint_rejects_overlong_custom_body(notify_client):
    from domains.events.registrations.models import EVENT_REMINDER_BODY_MAX_LENGTH

    client, mock_service = notify_client

    response = client.post(
        f"/portal/events/{uuid4()}/registrations/notify",
        json={"body": "x" * (EVENT_REMINDER_BODY_MAX_LENGTH + 1)},
    )

    assert response.status_code == 422
    mock_service.send_event_reminders.assert_not_called()


def test_event_reminder_template_contains_plain_text_and_escaped_html_details():
    html_body, text_body = templates.build_event_reminder_email(
        event_title="Founder & Builder <Night>",
        event_datetime="Tuesday, October 06, 2026 at 6:00 PM EDT",
        event_location="SF1101",
    )

    assert "<h1" in html_body
    assert "Reminder" in html_body
    assert "Founder &amp; Builder &lt;Night&gt;" in html_body
    assert "**Event:** Founder & Builder <Night>" in text_body
    assert "**Date & Time:** Tuesday, October 06, 2026 at 6:00 PM EDT" in text_body
    assert "**Location:** SF1101" in text_body
