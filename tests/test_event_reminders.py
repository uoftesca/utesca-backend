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
    )
    email_service_class.return_value.send_event_reminder.assert_any_call(
        to="two@example.com",
        event_title="UTESCA x Isaac: The Founder’s Test",
        event_datetime="Tuesday, October 06, 2026 at 6:00 PM EDT",
        event_location="SF1101",
    )


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
