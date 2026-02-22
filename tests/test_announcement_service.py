"""
Unit tests for the announcements service layer.

Covers:
- create_announcement: creates record, returns AnnouncementResponse, queues email task
- _should_send_to_user: all preference/priority combinations
- _filter_recipients_by_priority: urgent bypasses prefs, normal respects them
- mark_as_read: idempotency (existing record returned without duplicate insert)
- get_announcements: builds AnnouncementWithReadCount with correct read counts
- get_announcement: 404 when not found, is_read set from repository

Run with:
    pytest tests/test_announcement_service.py -v
"""

from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from domains.announcements.models import (
    AnnouncementCreate,
    AnnouncementReadResponse,
    AnnouncementResponse,
    AnnouncementWithReadCount,
)
from domains.announcements.service import AnnouncementService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_repository():
    """Mock AnnouncementRepository."""
    repo = Mock()
    repo.create_announcement = Mock()
    repo.get_announcement = Mock()
    repo.get_all = Mock()
    repo.mark_as_read = Mock()
    repo.has_user_read = Mock()
    repo.get_user_reads = Mock()
    repo.get_all_read_counts = Mock()
    repo.get_total_users_count = Mock()
    repo.update_announcement = Mock()
    repo.delete_announcement = Mock()
    return repo


@pytest.fixture
def announcement_service(mock_repository):
    """AnnouncementService with mocked repository and settings."""
    service = AnnouncementService.__new__(AnnouncementService)
    service.repository = mock_repository
    service.schema = "test"
    service.supabase = Mock()
    settings = Mock()
    settings.BASE_URL_PUBLIC = "https://portal.utesca.ca"
    service.settings = settings
    return service


@pytest.fixture
def sample_announcement():
    """Sample AnnouncementResponse from the repository."""
    return AnnouncementResponse(
        id=uuid4(),
        title="Test Announcement",
        content="This is a test announcement.",
        priority="normal",
        created_by=uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        is_read=False,
    )


@pytest.fixture
def sample_read_record(sample_announcement):
    """Sample AnnouncementReadResponse."""
    return AnnouncementReadResponse(
        id=uuid4(),
        announcement_id=sample_announcement.id,
        user_id=uuid4(),
        read_at=datetime.now(timezone.utc),
    )


# ============================================================================
# create_announcement
# ============================================================================


class TestCreateAnnouncement:
    """Tests for create_announcement."""

    def test_creates_announcement_and_returns_response(
        self, announcement_service, mock_repository, sample_announcement
    ):
        """Should create announcement in DB and return it."""
        mock_repository.create_announcement.return_value = sample_announcement
        request = AnnouncementCreate(title="Test", content="Body", priority="normal", send_email=False)
        user_id = uuid4()

        result = announcement_service.create_announcement(request, user_id)

        mock_repository.create_announcement.assert_called_once_with(
            title="Test",
            content="Body",
            priority="normal",
            created_by=user_id,
        )
        assert result == sample_announcement

    def test_queues_email_when_send_email_is_true(self, announcement_service, mock_repository, sample_announcement):
        """Should add background task when send_email=True."""
        mock_repository.create_announcement.return_value = sample_announcement
        request = AnnouncementCreate(title="Test", content="Body", priority="urgent", send_email=True)
        background_tasks = Mock()

        announcement_service.create_announcement(request, uuid4(), background_tasks)

        background_tasks.add_task.assert_called_once()

    def test_skips_email_when_send_email_is_false(self, announcement_service, mock_repository, sample_announcement):
        """Should not queue background task when send_email=False."""
        mock_repository.create_announcement.return_value = sample_announcement
        request = AnnouncementCreate(title="Test", content="Body", priority="normal", send_email=False)
        background_tasks = Mock()

        announcement_service.create_announcement(request, uuid4(), background_tasks)

        background_tasks.add_task.assert_not_called()

    def test_still_creates_when_background_tasks_unavailable(
        self, announcement_service, mock_repository, sample_announcement
    ):
        """Announcement should be created even if BackgroundTasks is not available."""
        mock_repository.create_announcement.return_value = sample_announcement
        request = AnnouncementCreate(title="Test", content="Body", send_email=True)

        result = announcement_service.create_announcement(request, uuid4(), background_tasks=None)

        assert result == sample_announcement

    def test_raises_500_on_repository_failure(self, announcement_service, mock_repository):
        """Should raise HTTP 500 when repository raises an unexpected error."""
        mock_repository.create_announcement.side_effect = Exception("DB error")
        request = AnnouncementCreate(title="Test", content="Body")

        with pytest.raises(HTTPException) as exc_info:
            announcement_service.create_announcement(request, uuid4())

        assert exc_info.value.status_code == 500


# ============================================================================
# _should_send_to_user
# ============================================================================


class TestShouldSendToUser:
    """Tests for _should_send_to_user filtering logic."""

    @pytest.mark.parametrize(
        "preference, priority, expected",
        [
            ("all", "urgent", True),
            ("all", "normal", True),
            ("urgent_only", "urgent", True),
            ("urgent_only", "normal", False),
            ("none", "urgent", False),
            ("none", "normal", False),
        ],
    )
    def test_filtering_matrix(self, announcement_service, preference, priority, expected):
        """Verifies all combinations of preference and priority."""
        result = announcement_service._should_send_to_user(preference, priority)
        assert result is expected


# ============================================================================
# _filter_recipients_by_priority
# ============================================================================


class TestFilterRecipientsByPriority:
    """Tests for _filter_recipients_by_priority."""

    def _make_user(self, email: str, pref: str) -> dict:
        return {
            "email": email,
            "notification_preferences": {"announcements": pref},
        }

    def test_urgent_sends_to_all_and_urgent_only_but_not_none(self, announcement_service):
        """Urgent announcements still respect 'none' preference (used to suppress emails during dev/testing)."""
        users = [
            self._make_user("a@test.com", "all"),
            self._make_user("b@test.com", "urgent_only"),
            self._make_user("c@test.com", "none"),
        ]

        result = announcement_service._filter_recipients_by_priority(users, "urgent")

        assert len(result) == 2
        emails = [u["email"] for u in result]
        assert "a@test.com" in emails
        assert "b@test.com" in emails
        assert "c@test.com" not in emails

    def test_normal_excludes_urgent_only_and_none(self, announcement_service):
        """Normal announcements only go to users with 'all' preference."""
        users = [
            self._make_user("a@test.com", "all"),
            self._make_user("b@test.com", "urgent_only"),
            self._make_user("c@test.com", "none"),
        ]

        result = announcement_service._filter_recipients_by_priority(users, "normal")

        assert len(result) == 1
        assert result[0]["email"] == "a@test.com"

    def test_user_without_preferences_defaults_to_all(self, announcement_service):
        """Users with no notification_preferences should default to receiving all."""
        users = [{"email": "a@test.com", "notification_preferences": None}]

        result = announcement_service._filter_recipients_by_priority(users, "normal")

        assert len(result) == 1

    def test_empty_user_list_returns_empty(self, announcement_service):
        result = announcement_service._filter_recipients_by_priority([], "normal")
        assert result == []


# ============================================================================
# mark_as_read
# ============================================================================


class TestMarkAsRead:
    """Tests for mark_as_read idempotency."""

    def test_creates_read_record_when_not_yet_read(self, announcement_service, mock_repository, sample_read_record):
        """Should insert a new read record when the announcement hasn't been read."""
        mock_repository.has_user_read.return_value = False
        mock_repository.mark_as_read.return_value = sample_read_record

        result = announcement_service.mark_as_read(sample_read_record.announcement_id, uuid4())

        mock_repository.mark_as_read.assert_called_once()
        assert result == sample_read_record

    def test_returns_existing_record_when_already_read(self, announcement_service, mock_repository, sample_read_record):
        """Should return existing read record without duplicate insert."""
        announcement_id = sample_read_record.announcement_id
        user_id = sample_read_record.user_id

        mock_repository.has_user_read.return_value = True
        mock_repository.get_user_reads.return_value = [sample_read_record]

        result = announcement_service.mark_as_read(announcement_id, user_id)

        mock_repository.mark_as_read.assert_not_called()
        assert result == sample_read_record

    def test_raises_500_on_repository_failure(self, announcement_service, mock_repository):
        """Should raise HTTP 500 when repository raises an unexpected error."""
        mock_repository.has_user_read.side_effect = Exception("DB error")

        with pytest.raises(HTTPException) as exc_info:
            announcement_service.mark_as_read(uuid4(), uuid4())

        assert exc_info.value.status_code == 500


# ============================================================================
# get_announcements
# ============================================================================


class TestGetAnnouncements:
    """Tests for get_announcements with read count aggregation."""

    def test_returns_announcements_with_read_counts(self, announcement_service, mock_repository, sample_announcement):
        """Should enrich announcements with total_reads and unread_count."""
        user_id = uuid4()
        aid = str(sample_announcement.id)

        mock_repository.get_all.return_value = ([sample_announcement], 1)
        mock_repository.get_all_read_counts.return_value = {aid: 3}
        mock_repository.get_user_reads.return_value = []
        mock_repository.get_total_users_count.return_value = 10

        result = announcement_service.get_announcements(user_id=user_id)

        assert result.total == 1
        item = result.announcements[0]
        assert isinstance(item, AnnouncementWithReadCount)
        assert item.total_reads == 3
        assert item.unread_count == 7

    def test_is_read_true_when_user_has_read(
        self, announcement_service, mock_repository, sample_announcement, sample_read_record
    ):
        """is_read should be True when the current user has read the announcement."""
        user_id = sample_read_record.user_id
        read_record = Mock()
        read_record.announcement_id = sample_announcement.id

        mock_repository.get_all.return_value = ([sample_announcement], 1)
        mock_repository.get_all_read_counts.return_value = {}
        mock_repository.get_user_reads.return_value = [read_record]
        mock_repository.get_total_users_count.return_value = 5

        result = announcement_service.get_announcements(user_id=user_id)

        assert result.announcements[0].is_read is True

    def test_is_read_false_when_user_has_not_read(self, announcement_service, mock_repository, sample_announcement):
        """is_read should be False when the current user has not read the announcement."""
        mock_repository.get_all.return_value = ([sample_announcement], 1)
        mock_repository.get_all_read_counts.return_value = {}
        mock_repository.get_user_reads.return_value = []
        mock_repository.get_total_users_count.return_value = 5

        result = announcement_service.get_announcements(user_id=uuid4())

        assert result.announcements[0].is_read is False

    def test_empty_announcement_list(self, announcement_service, mock_repository):
        """Should return empty list with total=0 when no announcements exist."""
        mock_repository.get_all.return_value = ([], 0)
        mock_repository.get_all_read_counts.return_value = {}
        mock_repository.get_user_reads.return_value = []
        mock_repository.get_total_users_count.return_value = 5

        result = announcement_service.get_announcements(user_id=uuid4())

        assert result.total == 0
        assert result.announcements == []

    def test_raises_400_for_invalid_page(self, announcement_service, mock_repository):
        """Should raise HTTP 400 when page < 1."""
        with pytest.raises(HTTPException) as exc_info:
            announcement_service.get_announcements(user_id=uuid4(), page=0, page_size=10)

        assert exc_info.value.status_code == 400


# ============================================================================
# get_announcement
# ============================================================================


class TestGetAnnouncement:
    """Tests for get_announcement (single)."""

    def test_returns_announcement_with_is_read_false(self, announcement_service, mock_repository, sample_announcement):
        """Should return announcement with is_read=False when user hasn't read it."""
        mock_repository.get_announcement.return_value = sample_announcement
        mock_repository.has_user_read.return_value = False

        result = announcement_service.get_announcement(sample_announcement.id, uuid4())

        assert result.is_read is False

    def test_returns_announcement_with_is_read_true(self, announcement_service, mock_repository, sample_announcement):
        """Should return announcement with is_read=True when user has read it."""
        mock_repository.get_announcement.return_value = sample_announcement
        mock_repository.has_user_read.return_value = True

        result = announcement_service.get_announcement(sample_announcement.id, uuid4())

        assert result.is_read is True

    def test_raises_404_when_not_found(self, announcement_service, mock_repository):
        """Should raise HTTP 404 when announcement does not exist."""
        mock_repository.get_announcement.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            announcement_service.get_announcement(uuid4(), uuid4())

        assert exc_info.value.status_code == 404
