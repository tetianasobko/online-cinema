from datetime import timedelta

import pytest

from security.exceptions import InvalidTokenError, TokenExpiredError
from security.token_manager import JWTAuthManager
from security.utils import generate_secure_token

pytestmark = pytest.mark.unit


@pytest.fixture
def jwt_manager() -> JWTAuthManager:
    return JWTAuthManager(
        secret_key_access="unit-test-access-secret",
        secret_key_refresh="unit-test-refresh-secret",
        algorithm="HS256",
    )


def test_generate_secure_token_returns_unique_hex_tokens() -> None:
    first_token = generate_secure_token()
    second_token = generate_secure_token()

    assert len(first_token) == 64
    assert all(character in "0123456789abcdef" for character in first_token)
    assert first_token != second_token


def test_access_token_round_trip(jwt_manager: JWTAuthManager) -> None:
    token = jwt_manager.create_access_token({"user_id": 7})

    payload = jwt_manager.decode_access_token(token)

    assert payload["user_id"] == 7
    assert "exp" in payload


def test_refresh_token_round_trip(jwt_manager: JWTAuthManager) -> None:
    token = jwt_manager.create_refresh_token({"user_id": 8})

    payload = jwt_manager.decode_refresh_token(token)

    assert payload["user_id"] == 8
    assert "exp" in payload


def test_access_token_cannot_be_used_as_refresh_token(
    jwt_manager: JWTAuthManager,
) -> None:
    access_token = jwt_manager.create_access_token({"user_id": 7})

    with pytest.raises(InvalidTokenError):
        jwt_manager.decode_refresh_token(access_token)


def test_expired_access_token_is_rejected(
    jwt_manager: JWTAuthManager,
) -> None:
    token = jwt_manager.create_access_token(
        {"user_id": 7},
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(TokenExpiredError):
        jwt_manager.decode_access_token(token)


def test_malformed_token_is_rejected(jwt_manager: JWTAuthManager) -> None:
    with pytest.raises(InvalidTokenError):
        jwt_manager.decode_access_token("not-a-jwt")
