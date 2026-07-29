import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database.models import (
    MovieModel,
    UserGroupEnum,
    UserGroupModel,
    UserModel,
)
from security.token_manager import JWTAuthManager

pytestmark = pytest.mark.integration


async def create_second_user_headers(
    db_session: AsyncSession,
) -> dict[str, str]:
    group = await db_session.scalar(
        select(UserGroupModel).where(
            UserGroupModel.name == UserGroupEnum.USER
        )
    )
    assert group is not None
    user = UserModel(
        email="second-user@example.com",
        hashed_password="unused-in-interaction-tests",
        is_active=True,
        group_id=group.id,
    )
    db_session.add(user)
    await db_session.commit()

    settings = get_settings()
    manager = JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM,
    )
    token = manager.create_access_token({"user_id": user.id})
    return {"Authorization": f"Bearer {token}"}


async def test_comment_reply_like_and_notification_workflow(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    movie = seeded_movies[0]
    second_headers = await create_second_user_headers(db_session)

    created = await client.post(
        f"/api/v1/movies/{movie.uuid}/comments",
        headers=auth_headers,
        json={"text": "A thoughtful comment"},
    )
    assert created.status_code == 201
    comment_id = created.json()["id"]

    reply = await client.post(
        f"/api/v1/comments/{comment_id}/replies",
        headers=second_headers,
        json={"text": "A useful reply"},
    )
    liked = await client.post(
        f"/api/v1/comments/{comment_id}/likes",
        headers=second_headers,
    )
    comments = await client.get(
        f"/api/v1/movies/{movie.uuid}/comments"
    )

    assert reply.status_code == 201
    assert liked.status_code == 201
    assert comments.status_code == 200
    returned_comment = comments.json()["comments"][0]
    assert returned_comment["likes_count"] == 1
    assert returned_comment["replies"][0]["text"] == "A useful reply"

    notifications = await client.get(
        "/api/v1/notifications/",
        headers=auth_headers,
    )
    assert notifications.status_code == 200
    data = notifications.json()
    assert data["total_items"] == 2
    assert {item["type"] for item in data["notifications"]} == {
        "comment_reply",
        "comment_like",
    }

    notification_id = data["notifications"][0]["id"]
    marked = await client.patch(
        f"/api/v1/notifications/{notification_id}/read",
        headers=auth_headers,
    )
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True

    read_all = await client.patch(
        "/api/v1/notifications/read-all",
        headers=auth_headers,
    )
    unread = await client.get(
        "/api/v1/notifications/",
        headers=auth_headers,
        params={"unread_only": True},
    )
    assert read_all.status_code == 200
    assert unread.json()["total_items"] == 0

    unliked = await client.delete(
        f"/api/v1/comments/{comment_id}/likes",
        headers=second_headers,
    )
    assert unliked.status_code == 200


async def test_comments_validate_text_and_parent_rules(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    movie = seeded_movies[0]
    second_headers = await create_second_user_headers(db_session)

    invalid = await client.post(
        f"/api/v1/movies/{movie.uuid}/comments",
        headers=auth_headers,
        json={"text": "   "},
    )
    assert invalid.status_code == 422

    parent = await client.post(
        f"/api/v1/movies/{movie.uuid}/comments",
        headers=auth_headers,
        json={"text": "Parent"},
    )
    reply = await client.post(
        f"/api/v1/comments/{parent.json()['id']}/replies",
        headers=second_headers,
        json={"text": "Reply"},
    )
    nested = await client.post(
        f"/api/v1/comments/{reply.json()['id']}/replies",
        headers=auth_headers,
        json={"text": "Nested reply"},
    )

    assert nested.status_code == 400
    assert nested.json()["detail"] == "Replies cannot have nested replies."
