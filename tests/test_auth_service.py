"""Tests for invitation and onboarding-link behavior."""

from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from supabase_auth.errors import AuthApiError

from domains.auth.models import InviteUserRequest, InviteUserResponse
from domains.auth.service import AuthService


@pytest.fixture
def onboarding_link_service():
    """Create an AuthService with its external clients mocked."""
    service = AuthService.__new__(AuthService)
    service.schema = "test"
    service.settings = SimpleNamespace(BASE_URL_PORTAL="http://localhost:3001")

    admin_client = Mock()
    profile_query = admin_client.schema.return_value.table.return_value
    profile_query.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    link_response = SimpleNamespace(
        properties=SimpleNamespace(
            hashed_token="generated-token-hash",
            verification_type="recovery",
        ),
        user=SimpleNamespace(
            user_metadata={
                "first_name": "Ada",
                "last_name": "Lovelace",
                "role": "director",
                "display_role": "Engineering Director",
            }
        ),
    )
    admin_client.auth.admin.generate_link.return_value = link_response
    return service, admin_client


def make_invite_request() -> InviteUserRequest:
    """Build a valid invitation request for fallback tests."""
    return InviteUserRequest(
        email="ada@example.com",
        first_name="Ada",
        last_name="Lovelace",
        role="director",
        display_role="Engineering Director",
        department_id=uuid4(),
    )


def test_invite_existing_user_sends_new_onboarding_link():
    """An existing Auth user should transparently receive a new onboarding link."""
    service = AuthService.__new__(AuthService)
    service.schema = "test"
    service.settings = SimpleNamespace(BASE_URL_PORTAL="http://localhost:3001")
    admin_client = Mock()
    admin_client.auth.admin.list_users.return_value = [SimpleNamespace(email="Ada@Example.com")]
    service._get_admin_client = Mock(return_value=admin_client)
    service._send_onboarding_link = Mock(
        return_value=InviteUserResponse(
            success=True,
            message="A new onboarding link was sent to ada@example.com",
            email="ada@example.com",
        )
    )

    result = service.invite_user(make_invite_request(), uuid4())

    service._send_onboarding_link.assert_called_once_with(
        admin_client,
        "ada@example.com",
    )
    admin_client.auth.admin.invite_user_by_email.assert_not_called()
    assert result.success is True
    assert result.message == "A new onboarding link was sent to ada@example.com"


def test_invite_does_not_send_link_after_unrelated_supabase_error():
    """An unrelated Auth error must not trigger an onboarding email."""
    service = AuthService.__new__(AuthService)
    service.schema = "test"
    service.settings = SimpleNamespace(BASE_URL_PORTAL="http://localhost:3001")
    admin_client = Mock()
    admin_client.auth.admin.list_users.return_value = []
    admin_client.auth.admin.invite_user_by_email.side_effect = AuthApiError(
        "Email rate limit exceeded",
        429,
        "over_email_send_rate_limit",
    )
    service._get_admin_client = Mock(return_value=admin_client)
    service._send_onboarding_link = Mock()

    with pytest.raises(HTTPException) as exc_info:
        service.invite_user(make_invite_request(), uuid4())

    assert exc_info.value.status_code == 500
    service._send_onboarding_link.assert_not_called()


def test_send_onboarding_link_generates_and_sends_custom_email(onboarding_link_service):
    """Recovery token should be delivered through the branded onboarding email."""
    service, admin_client = onboarding_link_service
    email_service = Mock()
    email_service.send_onboarding_link.return_value = True

    with patch("domains.auth.service.EmailService", return_value=email_service):
        result = service._send_onboarding_link(admin_client, "ada@example.com")

    admin_client.auth.admin.generate_link.assert_called_once_with(
        {
            "type": "recovery",
            "email": "ada@example.com",
        }
    )
    email_service.send_onboarding_link.assert_called_once_with(
        "ada@example.com",
        "Ada",
        "http://localhost:3001/accept-invite?token_hash=generated-token-hash&type=recovery",
    )
    assert result.success is True
    assert result.email == "ada@example.com"
