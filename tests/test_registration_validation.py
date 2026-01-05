import pytest

from domains.events.registrations.service import RegistrationService
from domains.events.registrations.models import FileMeta


class ValidationOnlyService(RegistrationService):
    """
    Thin subclass to avoid hitting Supabase during tests.
    We don't call __init__, and we only use validate_form_data directly.
    """

    def __init__(self):
        pass


def make_file(field_name: str, size: int, mime: str) -> FileMeta:
    return FileMeta.model_validate(
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "registration_id": None,
            "event_id": "00000000-0000-0000-0000-000000000002",
            "field_name": field_name,
            "file_url": "https://example.com/file.pdf",
            "file_name": "file.pdf",
            "file_size": size,
            "mime_type": mime,
            "upload_session_id": "session",
            "uploaded_at": "2024-01-01T00:00:00Z",
            "scheduled_deletion_date": None,
            "deleted": False,
            "deleted_at": None,
        }
    )


def test_required_text_field():
    service = ValidationOnlyService()
    form_schema = {"fields": [{"id": "full_name", "type": "text", "required": True}]}
    errors = service.validate_form_data(form_data={}, form_schema=form_schema, files_by_field={})
    assert errors and errors[0]["field"] == "full_name"


def test_choice_validation():
    service = ValidationOnlyService()
    form_schema = {
        "fields": [
            {
                "id": "size",
                "type": "select",
                "required": True,
                "options": ["S", "M", "L"],
            }
        ]
    }
    errors = service.validate_form_data(
        form_data={"size": "XL"}, form_schema=form_schema, files_by_field={}
    )
    assert errors and "allowed options" in errors[0]["message"]


def test_file_validation_size_and_type():
    service = ValidationOnlyService()
    form_schema = {
        "fields": [
            {
                "id": "resume",
                "type": "file",
                "required": True,
                "validation": {"maxSize": 1_000_000, "allowedTypes": ["application/pdf"]},
            }
        ]
    }
    files_by_field = {
        "resume": [make_file("resume", size=2_000_000, mime="application/pdf")],
    }
    errors = service.validate_form_data(
        form_data={}, form_schema=form_schema, files_by_field=files_by_field
    )
    assert errors and "must be <=" in errors[0]["message"]

    files_by_field = {
        "resume": [make_file("resume", size=500_000, mime="application/msword")],
    }
    errors = service.validate_form_data(
        form_data={}, form_schema=form_schema, files_by_field=files_by_field
    )
    assert errors and "must be one of" in errors[0]["message"]


def test_passes_valid_payload():
    service = ValidationOnlyService()
    form_schema = {
        "fields": [
            {"id": "full_name", "type": "text", "required": True},
            {
                "id": "resume",
                "type": "file",
                "required": False,
                "validation": {"maxSize": 1_000_000, "allowedTypes": ["application/pdf"]},
            },
        ]
    }
    files_by_field = {
        "resume": [make_file("resume", size=500_000, mime="application/pdf")],
    }
    errors = service.validate_form_data(
        form_data={"full_name": "Jane Doe"}, form_schema=form_schema, files_by_field=files_by_field
    )
    assert errors == []

