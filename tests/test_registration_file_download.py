"""
Integration tests for RegistrationService.download_files_as_zip.

Uses the same __new__ + injected-mock pattern as test_registration_service_rsvp.py.
httpx.Client is patched so no real HTTP calls are made.

Run:
    export PYTHONPATH=$PYTHONPATH:$(pwd)/src
    pytest tests/test_registration_file_download.py -v
"""

import zipfile
from io import BytesIO
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from domains.events.registrations.service import RegistrationService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_events_repo():
    repo = Mock()
    repo.get_by_id = Mock()
    return repo


@pytest.fixture
def mock_reg_repo():
    repo = Mock()
    repo.list_registrations = Mock()
    return repo


@pytest.fixture
def mock_files_repo():
    repo = Mock()
    repo.get_files_by_registration_ids = Mock()
    return repo


@pytest.fixture
def service(mock_events_repo, mock_reg_repo, mock_files_repo):
    svc = RegistrationService.__new__(RegistrationService)
    svc.events_repo = mock_events_repo
    svc.reg_repo = mock_reg_repo
    svc.files_repo = mock_files_repo
    svc.schema = "test"
    return svc


def _make_event(event_id=None, slug="test-event"):
    event = Mock()
    event.id = event_id or uuid4()
    event.slug = slug
    return event


def _make_registration(reg_id=None, event_id=None, form_data=None):
    reg = Mock()
    reg.id = reg_id or uuid4()
    reg.event_id = event_id or uuid4()
    reg.form_data = form_data or {"firstName": "Jane", "lastName": "Doe"}
    return reg


def _make_file_meta(
    reg_id, file_name="resume.pdf", field_name="resume", deleted=False, file_url="https://host/file.pdf"
):
    f = Mock()
    f.id = uuid4()
    f.registration_id = reg_id
    f.event_id = uuid4()
    f.field_name = field_name
    f.file_url = file_url
    f.file_name = file_name
    f.file_size = 1024
    f.mime_type = "application/pdf"
    f.deleted = deleted
    return f


# ============================================================================
# Happy path
# ============================================================================


class TestDownloadFilesAsZipHappyPath:
    """Multiple files from multiple registrations produce a valid ZIP."""

    def test_returns_slug_zip_bytes_and_zero_errors(self, service, mock_events_repo, mock_reg_repo, mock_files_repo):
        event_id = uuid4()
        event = _make_event(event_id=event_id, slug="networking-night")
        mock_events_repo.get_by_id.return_value = event

        reg1 = _make_registration(event_id=event_id, form_data={"firstName": "Alice", "lastName": "Smith"})
        reg2 = _make_registration(event_id=event_id, form_data={"firstName": "Bob", "lastName": "Lee"})
        mock_reg_repo.list_registrations.return_value = ([reg1, reg2], 2)

        file1 = _make_file_meta(reg1.id, file_name="resume.pdf", field_name="resume", file_url="https://host/a.pdf")
        file2 = _make_file_meta(reg2.id, file_name="cover.pdf", field_name="cover", file_url="https://host/b.pdf")
        mock_files_repo.get_files_by_registration_ids.return_value = [file1, file2]

        with patch("domains.events.registrations.service.httpx.Client") as MockClient:
            mock_resp = Mock()
            mock_resp.content = b"pdf-content-a"
            mock_resp.raise_for_status = Mock()
            mock_client_instance = Mock()
            mock_client_instance.get.return_value = mock_resp
            mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
            mock_client_instance.__exit__ = Mock(return_value=False)
            MockClient.return_value = mock_client_instance

            slug, zip_bytes, error_count = service.download_files_as_zip(event_id)

        assert slug == "networking-night"
        assert error_count == 0

        # Verify ZIP is valid and contains two files
        zf = zipfile.ZipFile(BytesIO(zip_bytes))
        names = zf.namelist()
        assert len(names) == 2
        # Both files should have content
        for name in names:
            assert zf.read(name) == b"pdf-content-a"

    def test_zip_filenames_follow_lastname_firstname_field_convention(
        self, service, mock_events_repo, mock_reg_repo, mock_files_repo
    ):
        event_id = uuid4()
        mock_events_repo.get_by_id.return_value = _make_event(event_id=event_id)

        reg = _make_registration(event_id=event_id, form_data={"firstName": "Jane", "lastName": "Doe"})
        mock_reg_repo.list_registrations.return_value = ([reg], 1)
        mock_files_repo.get_files_by_registration_ids.return_value = [
            _make_file_meta(reg.id, file_name="myfile.pdf", field_name="resume")
        ]

        with patch("domains.events.registrations.service.httpx.Client") as MockClient:
            mock_resp = Mock()
            mock_resp.content = b"data"
            mock_resp.raise_for_status = Mock()
            inst = Mock()
            inst.get.return_value = mock_resp
            inst.__enter__ = Mock(return_value=inst)
            inst.__exit__ = Mock(return_value=False)
            MockClient.return_value = inst

            _, zip_bytes, _ = service.download_files_as_zip(event_id)

        names = zipfile.ZipFile(BytesIO(zip_bytes)).namelist()
        assert names == ["Doe-Jane-resume.pdf"]


# ============================================================================
# Event not found
# ============================================================================


class TestDownloadFilesAsZipEventNotFound:
    def test_raises_404_when_event_missing(self, service, mock_events_repo):
        mock_events_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            service.download_files_as_zip(uuid4())

        assert exc_info.value.status_code == 404
        assert "Event not found" in exc_info.value.detail


# ============================================================================
# No accepted/confirmed registrations
# ============================================================================


class TestDownloadFilesAsZipNoRegistrations:
    def test_raises_404_when_no_matching_registrations(self, service, mock_events_repo, mock_reg_repo):
        mock_events_repo.get_by_id.return_value = _make_event()
        mock_reg_repo.list_registrations.return_value = ([], 0)

        with pytest.raises(HTTPException) as exc_info:
            service.download_files_as_zip(uuid4())

        assert exc_info.value.status_code == 404
        assert "No accepted or confirmed registrations" in exc_info.value.detail


# ============================================================================
# All file downloads fail
# ============================================================================


class TestDownloadFilesAsZipAllDownloadsFail:
    def test_raises_404_when_every_download_fails(self, service, mock_events_repo, mock_reg_repo, mock_files_repo):
        event_id = uuid4()
        mock_events_repo.get_by_id.return_value = _make_event(event_id=event_id)

        reg = _make_registration(event_id=event_id)
        mock_reg_repo.list_registrations.return_value = ([reg], 1)
        mock_files_repo.get_files_by_registration_ids.return_value = [
            _make_file_meta(reg.id, file_url="https://bad-host/x.pdf"),
            _make_file_meta(reg.id, file_name="b.pdf", file_url="https://bad-host/y.pdf"),
        ]

        # Every download raises an exception
        with patch("domains.events.registrations.service.httpx.Client") as MockClient:
            inst = Mock()
            inst.get.side_effect = Exception("connection refused")
            inst.__enter__ = Mock(return_value=inst)
            inst.__exit__ = Mock(return_value=False)
            MockClient.return_value = inst

            with pytest.raises(HTTPException) as exc_info:
                service.download_files_as_zip(event_id)

        assert exc_info.value.status_code == 404
        assert "All file downloads failed" in exc_info.value.detail


# ============================================================================
# Partial download failures
# ============================================================================


class TestDownloadFilesAsZipPartialFailure:
    def test_zip_contains_only_successful_downloads_and_reports_error_count(
        self, service, mock_events_repo, mock_reg_repo, mock_files_repo
    ):
        event_id = uuid4()
        mock_events_repo.get_by_id.return_value = _make_event(event_id=event_id)

        reg = _make_registration(event_id=event_id, form_data={"firstName": "X", "lastName": "Y"})
        mock_reg_repo.list_registrations.return_value = ([reg], 1)

        good_url = "https://host/good.pdf"
        bad_url = "https://host/bad.pdf"
        mock_files_repo.get_files_by_registration_ids.return_value = [
            _make_file_meta(reg.id, file_name="good.pdf", field_name="resume", file_url=good_url),
            _make_file_meta(reg.id, file_name="bad.pdf", field_name="cover", file_url=bad_url),
        ]

        def mock_get(url, **kwargs):
            resp = Mock()
            resp.raise_for_status = Mock()
            if url == good_url:
                resp.content = b"good-content"
                return resp
            raise Exception("download failed")

        with patch("domains.events.registrations.service.httpx.Client") as MockClient:
            inst = Mock()
            inst.get.side_effect = mock_get
            inst.__enter__ = Mock(return_value=inst)
            inst.__exit__ = Mock(return_value=False)
            MockClient.return_value = inst

            slug, zip_bytes, error_count = service.download_files_as_zip(event_id)

        assert error_count == 1
        names = zipfile.ZipFile(BytesIO(zip_bytes)).namelist()
        assert len(names) == 1
        assert "resume" in names[0]


# ============================================================================
# Deleted / orphaned files are excluded
# ============================================================================


class TestDownloadFilesAsZipDeletedFilesExcluded:
    def test_deleted_files_are_not_included_in_zip(self, service, mock_events_repo, mock_reg_repo, mock_files_repo):
        event_id = uuid4()
        mock_events_repo.get_by_id.return_value = _make_event(event_id=event_id)

        reg = _make_registration(event_id=event_id, form_data={"firstName": "A", "lastName": "B"})
        mock_reg_repo.list_registrations.return_value = ([reg], 1)

        active_file = _make_file_meta(reg.id, file_name="keep.pdf", field_name="resume", deleted=False)
        deleted_file = _make_file_meta(reg.id, file_name="gone.pdf", field_name="cover", deleted=True)
        # registration_id=None — orphaned file, should be excluded
        orphan_file = _make_file_meta(None, file_name="orphan.pdf", field_name="extra", deleted=False)
        mock_files_repo.get_files_by_registration_ids.return_value = [active_file, deleted_file, orphan_file]

        with patch("domains.events.registrations.service.httpx.Client") as MockClient:
            resp = Mock()
            resp.content = b"data"
            resp.raise_for_status = Mock()
            inst = Mock()
            inst.get.return_value = resp
            inst.__enter__ = Mock(return_value=inst)
            inst.__exit__ = Mock(return_value=False)
            MockClient.return_value = inst

            _, zip_bytes, error_count = service.download_files_as_zip(event_id)

        assert error_count == 0
        names = zipfile.ZipFile(BytesIO(zip_bytes)).namelist()
        # Only the active, non-orphan file should be present
        assert len(names) == 1
        assert "resume" in names[0]

    def test_raises_404_when_all_files_are_deleted(self, service, mock_events_repo, mock_reg_repo, mock_files_repo):
        event_id = uuid4()
        mock_events_repo.get_by_id.return_value = _make_event(event_id=event_id)

        reg = _make_registration(event_id=event_id)
        mock_reg_repo.list_registrations.return_value = ([reg], 1)
        mock_files_repo.get_files_by_registration_ids.return_value = [
            _make_file_meta(reg.id, deleted=True),
        ]

        with pytest.raises(HTTPException) as exc_info:
            service.download_files_as_zip(event_id)

        assert exc_info.value.status_code == 404
        assert "No downloadable files" in exc_info.value.detail


# ============================================================================
# Duplicate filenames are deduplicated
# ============================================================================


class TestDownloadFilesAsZipDeduplicate:
    def test_duplicate_names_get_numeric_suffixes(self, service, mock_events_repo, mock_reg_repo, mock_files_repo):
        event_id = uuid4()
        mock_events_repo.get_by_id.return_value = _make_event(event_id=event_id)

        # Two registrations with identical names and field — produces same base filename
        reg1 = _make_registration(event_id=event_id, form_data={"firstName": "Jane", "lastName": "Doe"})
        reg2 = _make_registration(event_id=event_id, form_data={"firstName": "Jane", "lastName": "Doe"})
        mock_reg_repo.list_registrations.return_value = ([reg1, reg2], 2)
        mock_files_repo.get_files_by_registration_ids.return_value = [
            _make_file_meta(reg1.id, file_name="resume.pdf", field_name="resume"),
            _make_file_meta(reg2.id, file_name="resume.pdf", field_name="resume"),
        ]

        with patch("domains.events.registrations.service.httpx.Client") as MockClient:
            resp = Mock()
            resp.content = b"x"
            resp.raise_for_status = Mock()
            inst = Mock()
            inst.get.return_value = resp
            inst.__enter__ = Mock(return_value=inst)
            inst.__exit__ = Mock(return_value=False)
            MockClient.return_value = inst

            _, zip_bytes, _ = service.download_files_as_zip(event_id)

        names = sorted(zipfile.ZipFile(BytesIO(zip_bytes)).namelist())
        assert names == ["Doe-Jane-resume-2.pdf", "Doe-Jane-resume.pdf"]


# ============================================================================
# Slug fallback when event.slug is empty
# ============================================================================


class TestDownloadFilesAsZipSlugFallback:
    def test_uses_event_id_when_slug_is_empty(self, service, mock_events_repo, mock_reg_repo, mock_files_repo):
        event_id = uuid4()
        event = _make_event(event_id=event_id, slug="")
        mock_events_repo.get_by_id.return_value = event

        reg = _make_registration(event_id=event_id)
        mock_reg_repo.list_registrations.return_value = ([reg], 1)
        mock_files_repo.get_files_by_registration_ids.return_value = [_make_file_meta(reg.id)]

        with patch("domains.events.registrations.service.httpx.Client") as MockClient:
            resp = Mock()
            resp.content = b"y"
            resp.raise_for_status = Mock()
            inst = Mock()
            inst.get.return_value = resp
            inst.__enter__ = Mock(return_value=inst)
            inst.__exit__ = Mock(return_value=False)
            MockClient.return_value = inst

            slug, _, _ = service.download_files_as_zip(event_id)

        assert slug == str(event_id)
