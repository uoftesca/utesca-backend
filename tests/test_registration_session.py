from uuid import uuid4

import pytest

from domains.events.registrations.session import RegistrationSessionError, RegistrationSessionService

SECRET = "a-secure-registration-session-secret"


def test_registration_session_round_trip():
    service = RegistrationSessionService(SECRET)
    registration_id = uuid4()

    encoded = service.create(registration_id)
    session = service.verify(encoded)

    assert session.registration_id == registration_id


def test_registration_session_rejects_wrong_signing_key():
    encoded = RegistrationSessionService(SECRET).create(uuid4())
    other_service = RegistrationSessionService("a-different-secure-session-secret")

    with pytest.raises(RegistrationSessionError, match="Invalid registration session"):
        other_service.verify(encoded)
