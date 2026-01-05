from domains.events.registrations.models import FileMeta
from domains.events.registrations.service import RegistrationService

# RUN TESTS:
# export PYTHONPATH=$PYTHONPATH:$(pwd)/src
# pytest --cov=src tests/test_registration_validation.py
# pytest --cov=src --cov-report=term-missing tests/test_registration_validation.py
# pytest --cov=src --cov-report=html tests/test_registration_validation.py
# Open htmlcov/index.html to see the results

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


def test_required_text_field_camelcase():
    """Test camelCase field name validation."""
    service = ValidationOnlyService()
    form_schema = {"fields": [{"id": "fullName", "type": "text", "required": True}]}
    errors = service.validate_form_data(form_data={}, form_schema=form_schema, files_by_field={})
    assert errors and errors[0]["field"] == "fullName"


def test_extract_name_camelcase():
    """Test name extraction with camelCase fields."""
    service = ValidationOnlyService()

    # Test fullName
    form_data = {"fullName": "Jane Doe"}
    assert service._extract_name(form_data) == "Jane Doe"

    # Test firstName + lastName
    form_data = {"firstName": "Jane", "lastName": "Doe"}
    assert service._extract_name(form_data) == "Jane Doe"


def test_extract_name_legacy_snake_case():
    """Test name extraction with legacy snake_case fields still works."""
    service = ValidationOnlyService()

    # Test full_name
    form_data = {"full_name": "Jane Doe"}
    assert service._extract_name(form_data) == "Jane Doe"

    # Test first_name + last_name
    form_data = {"first_name": "Jane", "last_name": "Doe"}
    assert service._extract_name(form_data) == "Jane Doe"


def test_extract_name_priority():
    """Test that camelCase takes priority over snake_case."""
    service = ValidationOnlyService()

    # When both exist, camelCase should win
    form_data = {"fullName": "Camel Case", "full_name": "Snake Case"}
    assert service._extract_name(form_data) == "Camel Case"

    # When both exist for first/last name, camelCase should win
    form_data = {
        "firstName": "Camel",
        "lastName": "Case",
        "first_name": "Snake",
        "last_name": "Case"
    }
    assert service._extract_name(form_data) == "Camel Case"

