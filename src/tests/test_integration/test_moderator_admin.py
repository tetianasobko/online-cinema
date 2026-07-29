from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database.models import (
    MovieModel,
    OrderItemModel,
    OrderModel,
    OrderStatusEnum,
    PaymentModel,
    PaymentStatusEnum,
    UserGroupEnum,
    UserGroupModel,
    UserModel,
)
from security.token_manager import JWTAuthManager

pytestmark = pytest.mark.integration


async def headers_for_role(
    db: AsyncSession,
    role: UserGroupEnum,
) -> dict[str, str]:
    group = await db.scalar(
        select(UserGroupModel).where(UserGroupModel.name == role)
    )
    assert group is not None
    user = UserModel(
        email=f"{role.value}@example.com",
        hashed_password="unused",
        is_active=True,
        group_id=group.id,
    )
    db.add(user)
    await db.commit()

    settings = get_settings()
    manager = JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM,
    )
    token = manager.create_access_token({"user_id": user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(
    ("path", "minimum_role"),
    [
        ("/api/v1/admin/genres/1", UserGroupEnum.MODERATOR),
        ("/api/v1/admin/users/1/cart", UserGroupEnum.ADMIN),
        ("/api/v1/admin/payments", UserGroupEnum.ADMIN),
    ],
)
async def test_management_routes_enforce_role_permissions(
    client: AsyncClient,
    seeded_user_groups: AsyncSession,
    auth_headers: dict[str, str],
    path: str,
    minimum_role: UserGroupEnum,
) -> None:
    anonymous = await client.get(path)
    ordinary_user = await client.get(path, headers=auth_headers)
    moderator_headers = await headers_for_role(
        seeded_user_groups,
        UserGroupEnum.MODERATOR,
    )
    moderator = await client.get(path, headers=moderator_headers)

    assert anonymous.status_code == 401
    assert ordinary_user.status_code == 403
    if minimum_role == UserGroupEnum.MODERATOR:
        assert moderator.status_code == 404
    else:
        assert moderator.status_code == 403


@pytest.mark.parametrize(
    "resource",
    ["actors", "directors", "genres"],
)
async def test_moderator_can_manage_named_catalog_entities(
    client: AsyncClient,
    seeded_user_groups: AsyncSession,
    resource: str,
) -> None:
    headers = await headers_for_role(
        seeded_user_groups,
        UserGroupEnum.MODERATOR,
    )
    base_url = f"/api/v1/admin/{resource}"

    created = await client.post(
        f"{base_url}/",
        json={"name": "Test Name"},
        headers=headers,
    )
    assert created.status_code == 201
    entity_id = created.json()["id"]

    duplicate = await client.post(
        f"{base_url}/",
        json={"name": "Test Name"},
        headers=headers,
    )
    fetched = await client.get(
        f"{base_url}/{entity_id}",
        headers=headers,
    )
    updated = await client.patch(
        f"{base_url}/{entity_id}",
        json={"name": "Updated Name"},
        headers=headers,
    )
    deleted = await client.delete(
        f"{base_url}/{entity_id}",
        headers=headers,
    )

    assert duplicate.status_code == 409
    assert fetched.status_code == 200
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated Name"
    assert deleted.status_code == 204


async def test_moderator_can_create_update_and_delete_movie(
    client: AsyncClient,
    seeded_user_groups: AsyncSession,
    seeded_movies: list[MovieModel],
) -> None:
    headers = await headers_for_role(
        seeded_user_groups,
        UserGroupEnum.MODERATOR,
    )
    reference = seeded_movies[0]
    payload = {
        "name": "Moderator Movie",
        "year": 2026,
        "time": 105,
        "imdb": 7.5,
        "votes": 10,
        "description": "A movie created through the management API.",
        "price": "9.50",
        "certification_id": reference.certification_id,
        "genre_ids": [reference.genres[0].id],
        "director_ids": [reference.directors[0].id],
        "star_ids": [reference.stars[0].id],
    }

    created = await client.post(
        "/api/v1/admin/movies/",
        json=payload,
        headers=headers,
    )
    assert created.status_code == 201
    movie_uuid = created.json()["uuid"]

    updated = await client.patch(
        f"/api/v1/admin/movies/{movie_uuid}",
        json={"price": "10.25"},
        headers=headers,
    )
    fetched = await client.get(
        f"/api/v1/admin/movies/{movie_uuid}",
        headers=headers,
    )
    deleted = await client.delete(
        f"/api/v1/admin/movies/{movie_uuid}",
        headers=headers,
    )

    assert updated.status_code == 200
    assert updated.json()["price"] == "10.25"
    assert fetched.status_code == 200
    assert deleted.status_code == 200


async def test_moderator_cannot_delete_movie_in_a_cart(
    client: AsyncClient,
    seeded_user_groups: AsyncSession,
    seeded_movies: list[MovieModel],
    auth_headers: dict[str, str],
) -> None:
    movie = seeded_movies[0]
    added = await client.post(
        f"/api/v1/cart/{movie.uuid}",
        headers=auth_headers,
    )
    assert added.status_code == 201
    moderator_headers = await headers_for_role(
        seeded_user_groups,
        UserGroupEnum.MODERATOR,
    )

    response = await client.delete(
        f"/api/v1/admin/movies/{movie.uuid}",
        headers=moderator_headers,
    )

    assert response.status_code == 409
    assert "user cart" in response.json()["detail"]


async def test_moderator_cannot_delete_purchased_movie(
    client: AsyncClient,
    seeded_user_groups: AsyncSession,
    seeded_movies: list[MovieModel],
    active_user: UserModel,
    db_session: AsyncSession,
) -> None:
    movie = seeded_movies[0]
    db_session.add(
        OrderModel(
            user_id=active_user.id,
            status=OrderStatusEnum.PAID,
            total_amount=movie.price,
            items=[
                OrderItemModel(
                    movie_id=movie.id,
                    price_at_order=movie.price,
                )
            ],
        )
    )
    await db_session.commit()
    headers = await headers_for_role(
        seeded_user_groups,
        UserGroupEnum.MODERATOR,
    )

    response = await client.delete(
        f"/api/v1/admin/movies/{movie.uuid}",
        headers=headers,
    )

    assert response.status_code == 409
    assert "has been purchased" in response.json()["detail"]


async def test_admin_can_inspect_user_cart(
    client: AsyncClient,
    seeded_user_groups: AsyncSession,
    seeded_movies: list[MovieModel],
    active_user: UserModel,
    auth_headers: dict[str, str],
) -> None:
    movie = seeded_movies[0]
    await client.post(
        f"/api/v1/cart/{movie.uuid}",
        headers=auth_headers,
    )
    admin_headers = await headers_for_role(
        seeded_user_groups,
        UserGroupEnum.ADMIN,
    )

    response = await client.get(
        f"/api/v1/admin/users/{active_user.id}/cart",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == active_user.id
    assert response.json()["total_items"] == 1
    assert response.json()["items"][0]["movie"]["name"] == movie.name


async def test_admin_can_filter_payment_report(
    client: AsyncClient,
    seeded_user_groups: AsyncSession,
    active_user: UserModel,
    db_session: AsyncSession,
) -> None:
    order = OrderModel(
        user_id=active_user.id,
        status=OrderStatusEnum.PAID,
        total_amount=Decimal("12.00"),
        items=[],
    )
    db_session.add(order)
    await db_session.flush()
    db_session.add_all(
        [
            PaymentModel(
                user_id=active_user.id,
                order_id=order.id,
                status=PaymentStatusEnum.SUCCESSFUL,
                amount=Decimal("12.00"),
                external_payment_id="cs_admin_success",
            ),
            PaymentModel(
                user_id=active_user.id,
                order_id=order.id,
                status=PaymentStatusEnum.CANCELED,
                amount=Decimal("12.00"),
                external_payment_id="cs_admin_canceled",
            ),
        ]
    )
    await db_session.commit()
    admin_headers = await headers_for_role(
        seeded_user_groups,
        UserGroupEnum.ADMIN,
    )

    response = await client.get(
        "/api/v1/admin/payments",
        params={
            "user_id": active_user.id,
            "status": "successful",
            "page": 1,
            "per_page": 10,
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["total_items"] == 1
    assert response.json()["payments"][0]["status"] == "successful"
    assert response.json()["payments"][0]["user_id"] == active_user.id
