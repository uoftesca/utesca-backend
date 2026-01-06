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
def registration_service(mock_registration_repo, mock_events_repo, mock_files_repo):
    """Create a RegistrationService instance with mocked dependencies."""
    service = RegistrationService.__new__(RegistrationService)
    service.reg_repo = mock_registration_repo
    service.events_repo = mock_events_repo
    service.files_repo = mock_files_repo
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
        """Should successfully decline an accepted registration."""
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
            result = registration_service.rsvp_decline(sample_registration.id)

        # Assert
        assert result == declined_registration
        registration_service.reg_repo.set_not_attending.assert_called_once()

    def test_successfully_declines_confirmed_registration(
        self, registration_service, sample_registration, sample_event, fixed_datetime
    ):
        """Should successfully decline a confirmed registration."""
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
            result = registration_service.rsvp_decline(sample_registration.id)

        # Assert
        assert result == declined_registration
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
        """Should return registration without error if already not_attending."""
        # Arrange
        sample_registration.status = "not_attending"
        sample_event.date_time = fixed_datetime + timedelta(days=2)
        registration_service.reg_repo.get_registration_public.return_value = sample_registration
        registration_service.events_repo.get_by_id.return_value = sample_event

        # Act
        with patch("domains.events.registrations.service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            result = registration_service.rsvp_decline(sample_registration.id)

        # Assert
        assert result == sample_registration
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
