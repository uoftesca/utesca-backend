"""
Unit tests for RSVP service layer methods.

These tests focus on the RSVP functionality including:
- Event datetime validation
- 24-hour RSVP cutoff logic
- RSVP details retrieval
- Attendance confirmation
- Attendance decline

Run tests with:
    export PYTHONPATH=$PYTHONPATH:$(pwd)/src
    pytest tests/test_rsvp_service.py -v
    pytest tests/test_rsvp_service.py -v --cov=domains.events.registrations.service
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from domains.events.registrations.service import (
    EVENT_NOT_FOUND,
    NOT_ELIGIBLE_FOR_CONFIRMATION,
    REGISTRATION_NOT_ACCESSIBLE,
    RSVP_CUTOFF_PASSED,
    RegistrationService,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_registration_repo():
    """Mock registration repository."""
    repo = Mock()
    repo.get_registration_public = Mock()
    repo.confirm_registration = Mock()
    repo.set_not_attending = Mock()
    return repo


@pytest.fixture
def mock_events_repo():
    """Mock events repository."""
    repo = Mock()
    repo.get_by_id = Mock()
    return repo


@pytest.fixture
def mock_files_repo():
    """Mock files repository."""
    return Mock()


@pytest.fixture
def mock_user_repo():
    """Mock user repository."""
    repo = Mock()
    repo.get_users_with_notification_enabled = Mock()
    return repo


@pytest.fixture
def registration_service(mock_registration_repo, mock_events_repo, mock_files_repo, mock_user_repo):
    """Create a RegistrationService instance with mocked dependencies."""
    service = RegistrationService.__new__(RegistrationService)
    service.reg_repo = mock_registration_repo
    service.events_repo = mock_events_repo
    service.files_repo = mock_files_repo
    service.user_repo = mock_user_repo
    service.schema = "public"
    return service


@pytest.fixture
def sample_registration():
    """Create a sample registration object."""
    registration = Mock()
    registration.id = uuid4()
    registration.event_id = uuid4()
    registration.status = "accepted"
    registration.submitted_at = datetime.now(timezone.utc)
    registration.confirmed_at = None
    return registration


@pytest.fixture
def sample_event():
    """Create a sample event object."""
    event = Mock()
    event.id = uuid4()
    event.title = "Test Event"
    event.date_time = datetime.now(timezone.utc) + timedelta(days=7)  # 7 days in future
    event.location = "Test Location"
    event.description = "Test Description"
    return event


@pytest.fixture
def fixed_datetime():
    """Fixed datetime for consistent testing."""
    return datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


# ============================================================================
# Helper Method Tests: _has_event_passed
# ============================================================================


class TestHasEventPassed:
    """Test suite for _has_event_passed helper method."""

    def test_event_in_future_returns_false(self, registration_service, fixed_datetime):
        """Should return False when event is in the future."""
        # Arrange
        future_event_date = fixed_datetime + timedelta(days=1)

        # Act
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            result = registration_service._has_event_passed(future_event_date)

        # Assert
        assert result is False

    def test_event_in_past_returns_true(self, registration_service, fixed_datetime):
        """Should return True when event is in the past."""
        # Arrange
        past_event_date = fixed_datetime - timedelta(days=1)

        # Act
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            result = registration_service._has_event_passed(past_event_date)

        # Assert
        assert result is True

    def test_event_exactly_now_returns_false(self, registration_service, fixed_datetime):
        """Should return False when event time equals current time."""
        # Arrange & Act
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            result = registration_service._has_event_passed(fixed_datetime)

        # Assert
        assert result is False

    def test_handles_timezone_naive_datetime(self, registration_service, fixed_datetime):
        """Should handle timezone-naive datetime by converting to UTC."""
        # Arrange
        naive_datetime = datetime(2025, 1, 10, 12, 0, 0)  # No timezone

        # Act
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            result = registration_service._has_event_passed(naive_datetime)

        # Assert
        assert result is True  # naive_datetime is interpreted as UTC, which is before fixed_datetime

    def test_handles_timezone_aware_datetime(self, registration_service, fixed_datetime):
        """Should handle timezone-aware datetime correctly."""
        # Arrange
        aware_datetime = datetime(2025, 1, 20, 12, 0, 0, tzinfo=timezone.utc)

        # Act
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            result = registration_service._has_event_passed(aware_datetime)

        # Assert
        assert result is False


# ============================================================================
# Helper Method Tests: _is_within_rsvp_cutoff
# ============================================================================


class TestIsWithinRsvpCutoff:
    """Test suite for _is_within_rsvp_cutoff helper method."""

    def test_event_more_than_24h_away_returns_false(self, registration_service, fixed_datetime):
        """Should return False when event is more than 24 hours away."""
        # Arrange
        event_date = fixed_datetime + timedelta(hours=25)

        # Act
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            result = registration_service._is_within_rsvp_cutoff(event_date)

        # Assert
        assert result is False

    def test_event_exactly_24h_away_returns_true(self, registration_service, fixed_datetime):
        """Should return True when event is exactly 24 hours away."""
        # Arrange
        event_date = fixed_datetime + timedelta(hours=24)

        # Act
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            result = registration_service._is_within_rsvp_cutoff(event_date)

        # Assert
        assert result is True

    def test_event_less_than_24h_away_returns_true(self, registration_service, fixed_datetime):
        """Should return True when event is less than 24 hours away."""
        # Arrange
        event_date = fixed_datetime + timedelta(hours=23)

        # Act
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            result = registration_service._is_within_rsvp_cutoff(event_date)

        # Assert
        assert result is True

    def test_event_in_1_hour_returns_true(self, registration_service, fixed_datetime):
        """Should return True when event is only 1 hour away."""
        # Arrange
        event_date = fixed_datetime + timedelta(hours=1)

        # Act
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            result = registration_service._is_within_rsvp_cutoff(event_date)

        # Assert
        assert result is True

    def test_handles_timezone_naive_datetime(self, registration_service, fixed_datetime):
        """Should handle timezone-naive datetime by converting to UTC."""
        # Arrange
        naive_event_date = datetime(2025, 1, 16, 11, 0, 0)  # 23 hours from fixed_datetime

        # Act
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            result = registration_service._is_within_rsvp_cutoff(naive_event_date)

        # Assert
        assert result is True

    def test_boundary_just_before_cutoff(self, registration_service, fixed_datetime):
        """Should return False when just before the 24-hour cutoff."""
        # Arrange
        event_date = fixed_datetime + timedelta(hours=24, seconds=1)

        # Act
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            result = registration_service._is_within_rsvp_cutoff(event_date)

        # Assert
        assert result is False


# ============================================================================
# Service Method Tests: rsvp_details
# ============================================================================


class TestRsvpDetails:
    """Test suite for rsvp_details method."""

    def test_returns_details_for_valid_registration(
        self, registration_service, sample_registration, sample_event, fixed_datetime
    ):
        """Should return registration, event, and metadata for valid registration."""
        # Arrange
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = sample_event
        sample_event.date_time = fixed_datetime + timedelta(days=2)

        # Act
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            registration, event, metadata = registration_service.rsvp_details(sample_registration.id)

        # Assert
        assert registration == sample_registration
        assert event == sample_event
        assert metadata["current_status"] == "accepted"
        assert metadata["can_confirm"] is True
        assert metadata["can_decline"] is True
        assert metadata["is_final"] is False
        assert metadata["event_has_passed"] is False
        assert metadata["within_rsvp_cutoff"] is False

    def test_raises_404_when_registration_not_found(self, registration_service):
        """Should raise 404 when registration doesn't exist."""
        # Arrange
        registration_service.reg_repo.get_registration_public.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            registration_service.rsvp_details(uuid4())

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == REGISTRATION_NOT_ACCESSIBLE

    def test_raises_404_when_event_not_found(self, registration_service, sample_registration):
        """Should raise 404 when event doesn't exist."""
        # Arrange
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            registration_service.rsvp_details(sample_registration.id)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == EVENT_NOT_FOUND

    def test_can_confirm_false_when_within_cutoff(
        self, registration_service, sample_registration, sample_event, fixed_datetime
    ):
        """Should set can_confirm to False when within 24-hour cutoff."""
        # Arrange
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = sample_event
        sample_event.date_time = fixed_datetime + timedelta(hours=23)  # Within cutoff

        # Act
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            _, _, metadata = registration_service.rsvp_details(sample_registration.id)

        # Assert
        assert metadata["within_rsvp_cutoff"] is True
        assert metadata["can_confirm"] is False
        assert metadata["can_decline"] is False

    def test_can_confirm_false_when_event_passed(
        self, registration_service, sample_registration, sample_event, fixed_datetime
    ):
        """Should set can_confirm to False when event has passed."""
        # Arrange
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = sample_event
        sample_event.date_time = fixed_datetime - timedelta(hours=1)  # Past event

        # Act
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            _, _, metadata = registration_service.rsvp_details(sample_registration.id)

        # Assert
        assert metadata["event_has_passed"] is True
        assert metadata["can_confirm"] is False
        assert metadata["can_decline"] is False

    def test_is_final_true_for_not_attending_status(
        self, registration_service, sample_registration, sample_event, fixed_datetime
    ):
        """Should set is_final to True for not_attending status."""
        # Arrange
        sample_registration.status = "not_attending"
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = sample_event
        sample_event.date_time = fixed_datetime + timedelta(days=2)

        # Act
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            _, _, metadata = registration_service.rsvp_details(sample_registration.id)

        # Assert
        assert metadata["is_final"] is True
        assert metadata["can_confirm"] is False
        assert metadata["can_decline"] is False

    def test_can_decline_true_for_confirmed_status(
        self, registration_service, sample_registration, sample_event, fixed_datetime
    ):
        """Should allow decline for confirmed status."""
        # Arrange
        sample_registration.status = "confirmed"
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = sample_event
        sample_event.date_time = fixed_datetime + timedelta(days=2)

        # Act
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            _, _, metadata = registration_service.rsvp_details(sample_registration.id)

        # Assert
        assert metadata["can_decline"] is True
        assert metadata["can_confirm"] is False  # Already confirmed


# ============================================================================
# Service Method Tests: rsvp_confirm
# ============================================================================


class TestRsvpConfirm:
    """Test suite for rsvp_confirm method."""

    def test_successfully_confirms_accepted_registration(
        self, registration_service, sample_registration, sample_event, fixed_datetime
    ):
        """Should successfully confirm an accepted registration."""
        # Arrange
        sample_event.date_time = fixed_datetime + timedelta(days=2)
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = sample_event

        confirmed_registration = Mock()
        confirmed_registration.status = "confirmed"
        registration_service.reg_repo.confirm_registration.return_value = confirmed_registration

        # Act
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            result = registration_service.rsvp_confirm(sample_registration.id)

        # Assert
        assert result == confirmed_registration
        registration_service.reg_repo.confirm_registration.assert_called_once()

    def test_raises_404_when_registration_not_found(self, registration_service):
        """Should raise 404 when registration doesn't exist."""
        # Arrange
        registration_service.reg_repo.get_registration_public.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            registration_service.rsvp_confirm(uuid4())

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == REGISTRATION_NOT_ACCESSIBLE

    def test_raises_404_when_event_not_found(self, registration_service, sample_registration):
        """Should raise 404 when event doesn't exist."""
        # Arrange
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            registration_service.rsvp_confirm(sample_registration.id)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == EVENT_NOT_FOUND

    def test_raises_400_when_event_has_passed(
        self, registration_service, sample_registration, sample_event, fixed_datetime
    ):
        """Should raise 400 when event has already passed."""
        # Arrange
        sample_event.date_time = fixed_datetime - timedelta(hours=1)
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = sample_event

        # Act & Assert
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            with pytest.raises(HTTPException) as exc_info:
                registration_service.rsvp_confirm(sample_registration.id)

        assert exc_info.value.status_code == 400
        assert "event has already passed" in exc_info.value.detail

    def test_raises_400_when_within_rsvp_cutoff(
        self, registration_service, sample_registration, sample_event, fixed_datetime
    ):
        """Should raise 400 when within 24-hour RSVP cutoff."""
        # Arrange
        sample_event.date_time = fixed_datetime + timedelta(hours=23)
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = sample_event

        # Act & Assert
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            with pytest.raises(HTTPException) as exc_info:
                registration_service.rsvp_confirm(sample_registration.id)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == RSVP_CUTOFF_PASSED

    def test_idempotent_for_already_confirmed(
        self, registration_service, sample_registration, sample_event, fixed_datetime
    ):
        """Should return registration without error if already confirmed."""
        # Arrange
        sample_registration.status = "confirmed"
        sample_event.date_time = fixed_datetime + timedelta(days=2)
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = sample_event

        # Act
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            result = registration_service.rsvp_confirm(sample_registration.id)

        # Assert
        assert result == sample_registration
        registration_service.reg_repo.confirm_registration.assert_not_called()

    def test_raises_400_for_non_accepted_status(
        self, registration_service, sample_registration, sample_event, fixed_datetime
    ):
        """Should raise 400 when registration status is not 'accepted'."""
        # Arrange
        sample_registration.status = "pending"
        sample_event.date_time = fixed_datetime + timedelta(days=2)
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = sample_event

        # Act & Assert
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            with pytest.raises(HTTPException) as exc_info:
                registration_service.rsvp_confirm(sample_registration.id)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == NOT_ELIGIBLE_FOR_CONFIRMATION

    def test_raises_500_when_update_fails(
        self, registration_service, sample_registration, sample_event, fixed_datetime
    ):
        """Should raise 500 when database update fails."""
        # Arrange
        sample_event.date_time = fixed_datetime + timedelta(days=2)
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = sample_event
        registration_service.reg_repo.confirm_registration.return_value = None

        # Act & Assert
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            with pytest.raises(HTTPException) as exc_info:
                registration_service.rsvp_confirm(sample_registration.id)

        assert exc_info.value.status_code == 500
        assert "Failed to confirm attendance" in exc_info.value.detail


# ============================================================================
# Service Method Tests: rsvp_decline
# ============================================================================


class TestRsvpDecline:
    """Test suite for rsvp_decline method."""

    def test_successfully_declines_accepted_registration(
        self, registration_service, sample_registration, sample_event, fixed_datetime
    ):
        """Should successfully decline an accepted registration and return 3-tuple."""
        # Arrange
        sample_event.date_time = fixed_datetime + timedelta(days=2)
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = sample_event

        declined_registration = Mock()
        declined_registration.status = "not_attending"
        registration_service.reg_repo.set_not_attending.return_value = declined_registration

        # Act
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            registration, previous_status, event = registration_service.rsvp_decline(sample_registration.id)

        # Assert
        assert registration == declined_registration
        assert previous_status == "accepted"
        assert event == sample_event
        registration_service.reg_repo.set_not_attending.assert_called_once()

    def test_successfully_declines_confirmed_registration(
        self, registration_service, sample_registration, sample_event, fixed_datetime
    ):
        """Should successfully decline a confirmed registration and capture previous status."""
        # Arrange
        sample_registration.status = "confirmed"
        sample_event.date_time = fixed_datetime + timedelta(days=2)
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = sample_event

        declined_registration = Mock()
        declined_registration.status = "not_attending"
        registration_service.reg_repo.set_not_attending.return_value = declined_registration

        # Act
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            registration, previous_status, event = registration_service.rsvp_decline(sample_registration.id)

        # Assert
        assert registration == declined_registration
        assert previous_status == "confirmed"  # This is key for notification logic
        assert event == sample_event
        registration_service.reg_repo.set_not_attending.assert_called_once()

    def test_raises_404_when_registration_not_found(self, registration_service):
        """Should raise 404 when registration doesn't exist."""
        # Arrange
        registration_service.reg_repo.get_registration_public.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            registration_service.rsvp_decline(uuid4())

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == REGISTRATION_NOT_ACCESSIBLE

    def test_raises_404_when_event_not_found(self, registration_service, sample_registration):
        """Should raise 404 when event doesn't exist."""
        # Arrange
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            registration_service.rsvp_decline(sample_registration.id)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == EVENT_NOT_FOUND

    def test_raises_400_when_event_has_passed(
        self, registration_service, sample_registration, sample_event, fixed_datetime
    ):
        """Should raise 400 when event has already passed."""
        # Arrange
        sample_event.date_time = fixed_datetime - timedelta(hours=1)
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = sample_event

        # Act & Assert
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            with pytest.raises(HTTPException) as exc_info:
                registration_service.rsvp_decline(sample_registration.id)

        assert exc_info.value.status_code == 400
        assert "event has already passed" in exc_info.value.detail

    def test_raises_400_when_within_rsvp_cutoff(
        self, registration_service, sample_registration, sample_event, fixed_datetime
    ):
        """Should raise 400 when within 24-hour RSVP cutoff."""
        # Arrange
        sample_event.date_time = fixed_datetime + timedelta(hours=23)
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = sample_event

        # Act & Assert
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            with pytest.raises(HTTPException) as exc_info:
                registration_service.rsvp_decline(sample_registration.id)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == RSVP_CUTOFF_PASSED

    def test_idempotent_for_already_not_attending(
        self, registration_service, sample_registration, sample_event, fixed_datetime
    ):
        """Should return 3-tuple without error if already not_attending."""
        # Arrange
        sample_registration.status = "not_attending"
        sample_event.date_time = fixed_datetime + timedelta(days=2)
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = sample_event

        # Act
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            registration, previous_status, event = registration_service.rsvp_decline(sample_registration.id)

        # Assert
        assert registration == sample_registration
        assert previous_status == "not_attending"
        assert event == sample_event
        registration_service.reg_repo.set_not_attending.assert_not_called()

    def test_raises_400_for_invalid_status(
        self, registration_service, sample_registration, sample_event, fixed_datetime
    ):
        """Should raise 400 when registration status is not accepted or confirmed."""
        # Arrange
        sample_registration.status = "pending"
        sample_event.date_time = fixed_datetime + timedelta(days=2)
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = sample_event

        # Act & Assert
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            with pytest.raises(HTTPException) as exc_info:
                registration_service.rsvp_decline(sample_registration.id)

        assert exc_info.value.status_code == 400
        assert "not eligible for declining" in exc_info.value.detail

    def test_raises_500_when_update_fails(
        self, registration_service, sample_registration, sample_event, fixed_datetime
    ):
        """Should raise 500 when database update fails."""
        # Arrange
        sample_event.date_time = fixed_datetime + timedelta(days=2)
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = sample_event
        registration_service.reg_repo.set_not_attending.return_value = None

        # Act & Assert
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            with pytest.raises(HTTPException) as exc_info:
                registration_service.rsvp_decline(sample_registration.id)

        assert exc_info.value.status_code == 500
        assert "Failed to decline attendance" in exc_info.value.detail


# ============================================================================
# Decline Notification Tests
# ============================================================================


class TestDeclineNotifications:
    """Test suite for RSVP decline notification functionality (UTESCA-69)."""

    def test_send_decline_notification_to_subscribed_users_success(
        self, registration_service, sample_registration, sample_event
    ):
        """Should send notifications to all subscribed users when declining from confirmed."""
        # Arrange
        sample_registration.status = "not_attending"
        sample_registration.form_data = {
            "email": "attendee@example.com",
            "first_name": "John",
            "last_name": "Doe",
        }
        sample_event.title = "Test Event"
        sample_event.location = "Test Location"
        sample_event.date_time = datetime(2025, 1, 20, 18, 0, tzinfo=timezone.utc)

        # Mock subscribed users
        mock_user1 = Mock()
        mock_user1.email = "vp1@utesca.ca"
        mock_user2 = Mock()
        mock_user2.email = "vp2@utesca.ca"
        registration_service.user_repo.get_users_with_notification_enabled.return_value = [
            mock_user1,
            mock_user2,
        ]

        # Act
        with patch("core.email.EmailService") as MockEmailService:
            mock_email_service = MockEmailService.return_value
            mock_email_service.send_rsvp_decline_notification.return_value = True

            registration_service.send_decline_notification_to_subscribed_users(
                sample_registration, sample_event, previous_status="confirmed"
            )

        # Assert
        registration_service.user_repo.get_users_with_notification_enabled.assert_called_once_with("rsvp_changes")
        mock_email_service.send_rsvp_decline_notification.assert_called_once()
        call_args = mock_email_service.send_rsvp_decline_notification.call_args
        assert call_args[1]["to_emails"] == ["vp1@utesca.ca", "vp2@utesca.ca"]
        assert call_args[1]["attendee_email"] == "attendee@example.com"
        assert call_args[1]["attendee_name"] == "John Doe"
        assert call_args[1]["event_title"] == "Test Event"
        assert call_args[1]["previous_status"] == "confirmed"

    def test_send_decline_notification_skips_for_accepted_status(
        self, registration_service, sample_registration, sample_event
    ):
        """Should skip notifications when declining from accepted (not confirmed)."""
        # Arrange
        sample_registration.form_data = {"email": "attendee@example.com"}

        # Act
        with patch("core.email.EmailService") as MockEmailService:
            mock_email_service = MockEmailService.return_value

            registration_service.send_decline_notification_to_subscribed_users(
                sample_registration, sample_event, previous_status="accepted"
            )

        # Assert - should return early, no email service calls
        registration_service.user_repo.get_users_with_notification_enabled.assert_not_called()
        mock_email_service.send_rsvp_decline_notification.assert_not_called()

    def test_send_decline_notification_handles_no_subscribers(
        self, registration_service, sample_registration, sample_event
    ):
        """Should handle case when no users are subscribed to notifications."""
        # Arrange
        sample_registration.form_data = {"email": "attendee@example.com"}
        registration_service.user_repo.get_users_with_notification_enabled.return_value = []

        # Act
        with patch("core.email.EmailService") as MockEmailService:
            mock_email_service = MockEmailService.return_value

            registration_service.send_decline_notification_to_subscribed_users(
                sample_registration, sample_event, previous_status="confirmed"
            )

        # Assert
        registration_service.user_repo.get_users_with_notification_enabled.assert_called_once()
        mock_email_service.send_rsvp_decline_notification.assert_not_called()

    def test_send_decline_notification_handles_missing_email(
        self, registration_service, sample_registration, sample_event
    ):
        """Should skip notifications if attendee email is missing."""
        # Arrange
        sample_registration.form_data = {"first_name": "John"}  # No email

        # Act
        with patch("core.email.EmailService") as MockEmailService:
            mock_email_service = MockEmailService.return_value

            registration_service.send_decline_notification_to_subscribed_users(
                sample_registration, sample_event, previous_status="confirmed"
            )

        # Assert - should query users but not send emails
        registration_service.user_repo.get_users_with_notification_enabled.assert_called_once()
        mock_email_service.send_rsvp_decline_notification.assert_not_called()

    def test_send_decline_notification_handles_exception_gracefully(
        self, registration_service, sample_registration, sample_event
    ):
        """Should log error but not raise exception if notification fails."""
        # Arrange
        sample_registration.form_data = {"email": "attendee@example.com"}
        registration_service.user_repo.get_users_with_notification_enabled.side_effect = Exception("Database error")

        # Act - should not raise exception
        registration_service.send_decline_notification_to_subscribed_users(
            sample_registration, sample_event, previous_status="confirmed"
        )

        # Assert - should complete without raising
        registration_service.user_repo.get_users_with_notification_enabled.assert_called_once()

    def test_handle_decline_notifications_sends_both_emails(
        self, registration_service, sample_registration, sample_event
    ):
        """Should send both decliner confirmation and subscriber notifications."""
        # Arrange
        sample_registration.form_data = {
            "email": "attendee@example.com",
            "first_name": "John",
        }
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = sample_event

        # Act
        with (
            patch.object(registration_service, "send_attendance_declined_email") as mock_send_declined,
            patch.object(
                registration_service, "send_decline_notification_to_subscribed_users"
            ) as mock_send_notifications,
        ):
            registration_service.handle_decline_notifications(sample_registration.id, previous_status="confirmed")

        # Assert
        mock_send_declined.assert_called_once_with(sample_registration, sample_event)
        mock_send_notifications.assert_called_once_with(sample_registration, sample_event, "confirmed")

    def test_handle_decline_notifications_handles_missing_registration(self, registration_service):
        """Should handle case when registration is not found."""
        # Arrange
        registration_service.reg_repo.get_registration_public.return_value = None

        # Act - should not raise exception
        registration_service.handle_decline_notifications(uuid4(), previous_status="confirmed")

        # Assert
        registration_service.events_repo.get_by_id.assert_not_called()

    def test_handle_decline_notifications_handles_missing_event(self, registration_service, sample_registration):
        """Should handle case when event is not found."""
        # Arrange
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = None

        # Act - should not raise exception
        registration_service.handle_decline_notifications(sample_registration.id, previous_status="confirmed")

        # Assert - should fetch registration but not proceed
        registration_service.reg_repo.get_registration_public.assert_called_once()


# ============================================================================
# Email Template Tests
# ============================================================================


class TestEmailTemplates:
    """Test suite for email template generation."""

    def test_build_rsvp_decline_notification_with_full_name(self):
        """Should build notification email with attendee full name."""
        from core.email.templates import build_rsvp_decline_notification

        # Arrange
        attendee_name = "John Doe"
        attendee_email = "john@example.com"
        event_title = "Networking Night"
        event_datetime = "Wednesday, January 15, 2025 at 6:00 PM EST"
        event_location = "Bahen Centre"
        previous_status = "confirmed"

        # Act
        html_body, text_body = build_rsvp_decline_notification(
            attendee_name,
            attendee_email,
            event_title,
            event_datetime,
            event_location,
            previous_status,
        )

        # Assert
        assert "John Doe" in html_body
        assert "john@example.com" in html_body
        assert "Networking Night" in html_body
        assert "confirmed" in html_body
        assert "Bahen Centre" in html_body

        assert "John Doe" in text_body
        assert "john@example.com" in text_body
        assert "Networking Night" in text_body

    def test_build_rsvp_decline_notification_without_name(self):
        """Should build notification email using email when name is not provided."""
        from core.email.templates import build_rsvp_decline_notification

        # Arrange
        attendee_name = None
        attendee_email = "anonymous@example.com"
        event_title = "Workshop"
        event_datetime = "Friday, January 17, 2025 at 2:00 PM EST"
        event_location = "Online"
        previous_status = "confirmed"

        # Act
        html_body, text_body = build_rsvp_decline_notification(
            attendee_name,
            attendee_email,
            event_title,
            event_datetime,
            event_location,
            previous_status,
        )

        # Assert - should use email as display name
        assert "anonymous@example.com" in html_body
        assert "Workshop" in html_body

        assert "anonymous@example.com" in text_body
        assert "Workshop" in text_body

    def test_build_rsvp_decline_notification_returns_both_formats(self):
        """Should return both HTML and plain text versions."""
        from core.email.templates import build_rsvp_decline_notification

        # Act
        html_body, text_body = build_rsvp_decline_notification(
            "Jane Smith",
            "jane@example.com",
            "Tech Talk",
            "Monday, January 20, 2025 at 5:00 PM EST",
            "GB Hall",
            "confirmed",
        )

        # Assert
        assert isinstance(html_body, str)
        assert isinstance(text_body, str)
        assert len(html_body) > 0
        assert len(text_body) > 0
        assert "<html" in html_body.lower() or "<table" in html_body.lower()
        assert "<html" not in text_body.lower()


# ============================================================================
# Email Service Tests
# ============================================================================


class TestEmailService:
    """Test suite for EmailService RSVP decline notification method."""

    def test_send_rsvp_decline_notification_success(self):
        """Should send individual emails to all recipients and return True."""
        from core.email.service import EmailService

        # Arrange
        email_service = EmailService.__new__(EmailService)
        email_service.send_email = Mock(return_value=True)

        to_emails = ["vp1@utesca.ca", "vp2@utesca.ca"]
        attendee_name = "John Doe"
        attendee_email = "john@example.com"
        event_title = "Networking Event"
        event_datetime = "January 15, 2025 at 6:00 PM"
        event_location = "Bahen Centre"
        previous_status = "confirmed"

        # Act
        result = email_service.send_rsvp_decline_notification(
            to_emails,
            attendee_name,
            attendee_email,
            event_title,
            event_datetime,
            event_location,
            previous_status,
        )

        # Assert
        assert result is True
        assert email_service.send_email.call_count == 2
        # Verify each recipient got an individual email
        calls = email_service.send_email.call_args_list
        assert calls[0][1]["to"] == "vp1@utesca.ca"
        assert calls[1][1]["to"] == "vp2@utesca.ca"

    def test_send_rsvp_decline_notification_returns_false_for_empty_list(self):
        """Should return False when recipient list is empty."""
        from core.email.service import EmailService

        # Arrange
        email_service = EmailService.__new__(EmailService)
        email_service.send_email = Mock()

        # Act
        result = email_service.send_rsvp_decline_notification(
            [], "John", "john@example.com", "Event", "Date", "Location", "confirmed"
        )

        # Assert
        assert result is False
        email_service.send_email.assert_not_called()

    def test_send_rsvp_decline_notification_partial_success(self):
        """Should return True if at least one email succeeds."""
        from core.email.service import EmailService

        # Arrange
        email_service = EmailService.__new__(EmailService)
        # First email succeeds, second fails
        email_service.send_email = Mock(side_effect=[True, False])

        to_emails = ["success@example.com", "fail@example.com"]

        # Act
        result = email_service.send_rsvp_decline_notification(
            to_emails, "John", "john@example.com", "Event", "Date", "Location", "confirmed"
        )

        # Assert
        assert result is True
        assert email_service.send_email.call_count == 2

    def test_send_rsvp_decline_notification_handles_template_error(self):
        """Should return False and log error if template building fails."""
        from core.email.service import EmailService

        # Arrange
        email_service = EmailService.__new__(EmailService)
        email_service.send_email = Mock()

        # Act - mock template builder to raise exception
        with patch(
            "core.email.service.build_rsvp_decline_notification",
            side_effect=Exception("Template error"),
        ):
            result = email_service.send_rsvp_decline_notification(
                ["test@example.com"], "Name", "email@test.com", "Event", "Date", "Location", "confirmed"
            )

        # Assert
        assert result is False
        email_service.send_email.assert_not_called()


# ============================================================================
# Edge Case and Integration Tests
# ============================================================================


class TestEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    def test_cutoff_boundary_exactly_24_hours(
        self, registration_service, sample_registration, sample_event, fixed_datetime
    ):
        """Should block RSVP changes at exactly 24 hours before event."""
        # Arrange
        sample_event.date_time = fixed_datetime + timedelta(hours=24, minutes=0, seconds=0)
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = sample_event

        # Act & Assert
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            with pytest.raises(HTTPException) as exc_info:
                registration_service.rsvp_confirm(sample_registration.id)

        assert exc_info.value.detail == RSVP_CUTOFF_PASSED

    def test_cutoff_boundary_just_after_24_hours(
        self, registration_service, sample_registration, sample_event, fixed_datetime
    ):
        """Should allow RSVP changes just after 24-hour cutoff (24h + 1s)."""
        # Arrange
        sample_event.date_time = fixed_datetime + timedelta(hours=24, seconds=1)
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = sample_event

        confirmed_registration = Mock()
        confirmed_registration.status = "confirmed"
        registration_service.reg_repo.confirm_registration.return_value = confirmed_registration

        # Act
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            result = registration_service.rsvp_confirm(sample_registration.id)

        # Assert
        assert result == confirmed_registration

    def test_event_passed_takes_precedence_over_cutoff(
        self, registration_service, sample_registration, sample_event, fixed_datetime
    ):
        """Should show 'event passed' error instead of cutoff error when event is in past."""
        # Arrange
        sample_event.date_time = fixed_datetime - timedelta(hours=1)
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = sample_event

        # Act & Assert
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            with pytest.raises(HTTPException) as exc_info:
                registration_service.rsvp_confirm(sample_registration.id)

        assert "event has already passed" in exc_info.value.detail
        assert exc_info.value.detail != RSVP_CUTOFF_PASSED
