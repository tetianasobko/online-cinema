from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    ActivationTokenModel,
    PasswordResetTokenModel,
    UserModel,
)
from tests.doubles.stubs import StubEmailSender

pytestmark = pytest.mark.integration

EMAIL = "user@example.com"
PASSWORD = "StrongPassword123"


async def register_user(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/accounts/register",
        json={"email": EMAIL, "password": PASSWORD},
    )
    assert response.status_code == 201


async def activate_registered_user(db_session: AsyncSession) -> UserModel:
    user = await db_session.scalar(
        select(UserModel).where(UserModel.email == EMAIL)
    )
    assert user is not None
    user.is_active = True
    await db_session.commit()
    return user


async def test_register_user_creates_token_and_sends_email(
    client: AsyncClient,
    seeded_user_groups: AsyncSession,
    email_sender_stub: StubEmailSender,
) -> None:
    await register_user(client)

    user = await seeded_user_groups.scalar(
        select(UserModel).where(UserModel.email == EMAIL)
    )
    assert user is not None
    assert user.is_active is False

    token = await seeded_user_groups.scalar(
        select(ActivationTokenModel).where(
            ActivationTokenModel.user_id == user.id
        )
    )
    assert token is not None
    assert len(email_sender_stub.activation_emails) == 1
    assert email_sender_stub.activation_emails[0][0] == EMAIL
    assert token.token in email_sender_stub.activation_emails[0][1]


async def test_register_user_rejects_duplicate_email(
    client: AsyncClient,
    seeded_user_groups: AsyncSession,
) -> None:
    await register_user(client)

    response = await client.post(
        "/api/v1/accounts/register",
        json={"email": EMAIL, "password": PASSWORD},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "A user with this email already exists."
    )


async def test_register_user_rejects_weak_password(
    client: AsyncClient,
    seeded_user_groups: AsyncSession,
) -> None:
    response = await client.post(
        "/api/v1/accounts/register",
        json={"email": EMAIL, "password": "weak"},
    )

    assert response.status_code == 422
    assert "Password must contain at least 8 characters." in str(
        response.json()
    )


async def test_activate_account_with_valid_token(
    client: AsyncClient,
    seeded_user_groups: AsyncSession,
) -> None:
    await register_user(client)
    user = await seeded_user_groups.scalar(
        select(UserModel).where(UserModel.email == EMAIL)
    )
    assert user is not None
    token = await seeded_user_groups.scalar(
        select(ActivationTokenModel).where(
            ActivationTokenModel.user_id == user.id
        )
    )
    assert token is not None

    response = await client.get(
        "/api/v1/accounts/activate",
        params={"email": EMAIL, "token": token.token},
    )

    assert response.status_code == 200
    await seeded_user_groups.refresh(user)
    assert user.is_active is True
    stored_token_id = await seeded_user_groups.scalar(
        select(ActivationTokenModel.id).where(
            ActivationTokenModel.id == token.id
        )
    )
    assert stored_token_id is None


async def test_activate_account_rejects_expired_token(
    client: AsyncClient,
    seeded_user_groups: AsyncSession,
) -> None:
    await register_user(client)
    token = await seeded_user_groups.scalar(select(ActivationTokenModel))
    assert token is not None
    token.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await seeded_user_groups.commit()

    response = await client.get(
        "/api/v1/accounts/activate",
        params={"email": EMAIL, "token": token.token},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Invalid or expired activation token."
    )


async def test_login_refresh_and_logout_workflow(
    client: AsyncClient,
    seeded_user_groups: AsyncSession,
) -> None:
    await register_user(client)
    await activate_registered_user(seeded_user_groups)

    login_response = await client.post(
        "/api/v1/accounts/login",
        json={"email": EMAIL, "password": PASSWORD},
    )
    assert login_response.status_code == 201
    tokens = login_response.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    refresh_response = await client.post(
        "/api/v1/accounts/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"]

    logout_response = await client.post(
        "/api/v1/accounts/logout",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert logout_response.status_code == 200

    revoked_response = await client.post(
        "/api/v1/accounts/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert revoked_response.status_code == 401


async def test_login_rejects_inactive_user(
    client: AsyncClient,
    seeded_user_groups: AsyncSession,
) -> None:
    await register_user(client)

    response = await client.post(
        "/api/v1/accounts/login",
        json={"email": EMAIL, "password": PASSWORD},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "User account is not activated."


async def test_authenticated_user_can_change_password(
    client: AsyncClient,
    seeded_user_groups: AsyncSession,
) -> None:
    await register_user(client)
    await activate_registered_user(seeded_user_groups)
    login_response = await client.post(
        "/api/v1/accounts/login",
        json={"email": EMAIL, "password": PASSWORD},
    )
    access_token = login_response.json()["access_token"]

    response = await client.post(
        "/api/v1/accounts/password/change",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "old_password": PASSWORD,
            "new_password": "NewStrongPassword456",
        },
    )

    assert response.status_code == 200
    old_login = await client.post(
        "/api/v1/accounts/login",
        json={"email": EMAIL, "password": PASSWORD},
    )
    new_login = await client.post(
        "/api/v1/accounts/login",
        json={"email": EMAIL, "password": "NewStrongPassword456"},
    )
    assert old_login.status_code == 401
    assert new_login.status_code == 201


async def test_password_reset_replaces_password(
    client: AsyncClient,
    seeded_user_groups: AsyncSession,
    email_sender_stub: StubEmailSender,
) -> None:
    await register_user(client)
    await activate_registered_user(seeded_user_groups)

    request_response = await client.post(
        "/api/v1/accounts/password/reset/request",
        json={"email": EMAIL},
    )
    assert request_response.status_code == 200
    assert len(email_sender_stub.password_reset_emails) == 1

    reset_token = await seeded_user_groups.scalar(
        select(PasswordResetTokenModel)
    )
    assert reset_token is not None
    complete_response = await client.post(
        "/api/v1/accounts/password/reset/complete",
        json={
            "email": EMAIL,
            "token": reset_token.token,
            "new_password": "ResetStrongPassword789",
        },
    )

    assert complete_response.status_code == 200
    login_response = await client.post(
        "/api/v1/accounts/login",
        json={"email": EMAIL, "password": "ResetStrongPassword789"},
    )
    assert login_response.status_code == 201
