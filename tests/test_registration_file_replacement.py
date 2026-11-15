from types import SimpleNamespace
from unittest.mock import MagicMock, call
from uuid import uuid4

from domains.events.registrations.models import FileUploadRequest
from domains.events.registrations.service import RegistrationService


def test_upload_replaces_previous_unlinked_files():
    service = RegistrationService.__new__(RegistrationService)
    service.files_repo = MagicMock()
    event = SimpleNamespace(id=uuid4())
    previous_files = [SimpleNamespace(id=uuid4()), SimpleNamespace(id=uuid4())]
    created_file = SimpleNamespace(id=uuid4())
    service._get_event_or_404 = MagicMock(return_value=event)
    service.files_repo.get_file_for_field.return_value = previous_files
    service.files_repo.create_file_record.return_value = created_file
    payload = FileUploadRequest(
        upload_session_id="session-id",
        field_name="resume",
        file_url="https://example.com/resume.pdf",
        file_name="resume.pdf",
        file_size=1024,
        mime_type="application/pdf",
        event_id=event.id,
    )

    result = service.upload_file("event-slug", payload)

    assert result is created_file
    service.files_repo.delete_file_by_id.assert_has_calls(
        [
            call(previous_files[0].id),
            call(previous_files[1].id),
        ]
    )
