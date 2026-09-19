from utils.tokens import generate_token, hash_token


def test_generate_token_is_url_safe_and_random():
    first = generate_token()
    second = generate_token()

    assert first != second
    assert len(first) >= 43
    assert all(character.isalnum() or character in "-_" for character in first)


def test_hash_token_is_deterministic_and_does_not_return_raw_token():
    raw_token = "example-token"

    assert hash_token(raw_token) == hash_token(raw_token)
    assert hash_token(raw_token) != raw_token
    assert len(hash_token(raw_token)) == 64


def test_hash_token_rejects_empty_value():
    try:
        hash_token("")
    except ValueError as exc:
        assert str(exc) == "Token cannot be empty"
    else:
        raise AssertionError("Expected ValueError")
