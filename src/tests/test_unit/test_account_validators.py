import pytest

from database.validators.accounts import (
    validate_email,
    validate_password_strength,
)

pytestmark = pytest.mark.unit


def test_validate_email_normalizes_address() -> None:
    assert validate_email("Test.User@EXAMPLE.COM") == "test.user@example.com"


@pytest.mark.parametrize(
    "email",
    [
        "missing-at-sign",
        "@example.com",
        "user@",
    ],
)
def test_validate_email_rejects_invalid_address(email: str) -> None:
    with pytest.raises(ValueError):
        validate_email(email)


def test_validate_password_strength_accepts_strong_password() -> None:
    password = "StrongPassword123"

    assert validate_password_strength(password) == password


@pytest.mark.parametrize(
    ("password", "message"),
    [
        ("Short1A", "Password must contain at least 8 characters."),
        ("lowercase123", "Password must contain an uppercase letter."),
        ("UPPERCASE123", "Password must contain a lowercase letter."),
        ("NoDigitsHere", "Password must contain a digit."),
    ],
)
def test_validate_password_strength_rejects_weak_password(
    password: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_password_strength(password)
