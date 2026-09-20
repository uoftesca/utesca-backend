from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest

from domains.tokens.models import TokenRecord
from domains.tokens.service import TokenService, TokenValidationError
from utils.tokens import hash_token


def make_token(**overrides) -> TokenRecord:
    now = datetime.now(timezone.utc)
    values = {
        "id": uuid4(),
        "type": "verification",
        "token_hash": hash_token("raw-token"),
        "expires_at": now + timedelta(hours=1),
        "used_at": None,
        "revoked_at": None,
        "revoked_reason": None,
        "last_verified_at": None,
        "verification_count": 0,
        "created_at": now,
    }
    values.update(overrides)
    return TokenRecord.model_validate(values)


def test_issue_stores_only_hash():
    repository = Mock()
    repository.create.side_effect = lambda token_type, token_hash, expires_at: make_token(
        type=token_type,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    service = TokenService(repository)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

    issued = service.issue("verification", expires_at)

    assert issued.value != issued.record.token_hash
    assert hash_token(issued.value) == issued.record.token_hash
    assert issued.record.expires_at == expires_at


def test_issue_rejects_expired_or_naive_expiration():
    service = TokenService(Mock())

    with pytest.raises(ValueError, match="future"):
        service.issue("verification", datetime.now(timezone.utc) - timedelta(seconds=1))

    with pytest.raises(ValueError, match="timezone"):
        service.issue("verification", datetime.now())


def test_verify_consumes_one_time_token():
    repository = Mock()
    token = make_token()
    consumed = token.model_copy(update={"used_at": datetime.now(timezone.utc)})
    repository.get_by_id.return_value = token
    repository.consume.return_value = consumed
    service = TokenService(repository)

    result = service.verify(token.id, "raw-token", "verification", consume=True)

    assert result.used_at is not None
    repository.consume.assert_called_once()
    repository.record_verification.assert_not_called()


def test_verify_records_reusable_token_usage():
    repository = Mock()
    token = make_token(type="management")
    verified = token.model_copy(update={"verification_count": 1})
    repository.get_by_id.return_value = token
    repository.record_verification.return_value = verified
    service = TokenService(repository)

    result = service.verify(token.id, "raw-token", "management", consume=False)

    assert result.verification_count == 1
    repository.record_verification.assert_called_once()
    repository.consume.assert_not_called()


@pytest.mark.parametrize(
    "token",
    [
        None,
        make_token(token_hash=hash_token("wrong-token")),
        make_token(type="ticket"),
        make_token(revoked_at=datetime.now(timezone.utc)),
        make_token(used_at=datetime.now(timezone.utc)),
        make_token(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)),
    ],
)
def test_verify_rejects_invalid_tokens(token):
    repository = Mock()
    repository.get_by_id.return_value = token
    service = TokenService(repository)

    with pytest.raises(TokenValidationError, match="Invalid token"):
        service.verify(uuid4(), "raw-token", "verification", consume=True)

    repository.consume.assert_not_called()
    repository.record_verification.assert_not_called()
