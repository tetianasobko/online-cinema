import pytest

from security.passwords import hash_password, verify_password

pytestmark = pytest.mark.unit


def test_hash_password_does_not_store_plain_text() -> None:
    password = "StrongPassword123"

    hashed_password = hash_password(password)

    assert hashed_password != password
    assert verify_password(password, hashed_password)


def test_verify_password_rejects_wrong_password() -> None:
    hashed_password = hash_password("StrongPassword123")

    assert not verify_password("WrongPassword123", hashed_password)
