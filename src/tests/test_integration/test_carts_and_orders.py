from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    MovieModel,
    OrderItemModel,
    OrderModel,
    OrderStatusEnum,
    UserModel,
)

pytestmark = pytest.mark.integration


async def add_to_cart(
    client: AsyncClient,
    movie: MovieModel,
    auth_headers: dict[str, str],
) -> None:
    response = await client.post(
        f"/api/v1/cart/{movie.uuid}",
        headers=auth_headers,
    )
    assert response.status_code == 201


async def test_cart_add_view_remove_and_duplicate_rules(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
    auth_headers: dict[str, str],
) -> None:
    movie = seeded_movies[0]

    await add_to_cart(client, movie, auth_headers)
    duplicate = await client.post(
        f"/api/v1/cart/{movie.uuid}",
        headers=auth_headers,
    )
    cart = await client.get("/api/v1/cart/", headers=auth_headers)
    removed = await client.delete(
        f"/api/v1/cart/{movie.uuid}",
        headers=auth_headers,
    )
    missing = await client.delete(
        f"/api/v1/cart/{movie.uuid}",
        headers=auth_headers,
    )

    assert duplicate.status_code == 409
    assert cart.status_code == 200
    assert cart.json()["total_items"] == 1
    assert cart.json()["items"][0]["movie"]["name"] == movie.name
    assert cart.json()["total_price"] == "5.99"
    assert removed.status_code == 200
    assert missing.status_code == 404


async def test_cart_can_be_cleared(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
    auth_headers: dict[str, str],
) -> None:
    await add_to_cart(client, seeded_movies[0], auth_headers)
    await add_to_cart(client, seeded_movies[1], auth_headers)

    response = await client.delete("/api/v1/cart/", headers=auth_headers)
    cart = await client.get("/api/v1/cart/", headers=auth_headers)

    assert response.status_code == 200
    assert cart.json()["total_items"] == 0
    assert cart.json()["total_price"] == "0.00"


async def test_cart_rejects_unavailable_movie(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    movie = seeded_movies[0]
    movie.price = None
    await db_session.commit()

    response = await client.post(
        f"/api/v1/cart/{movie.uuid}",
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "This movie is not available for purchase."
    )


async def test_cart_rejects_purchased_movie(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
    active_user: UserModel,
    auth_headers: dict[str, str],
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

    response = await client.post(
        f"/api/v1/cart/{movie.uuid}",
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert "already been purchased" in response.json()["detail"]


async def test_create_list_and_cancel_order(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
    auth_headers: dict[str, str],
) -> None:
    await add_to_cart(client, seeded_movies[0], auth_headers)
    await add_to_cart(client, seeded_movies[1], auth_headers)

    created = await client.post("/api/v1/orders/", headers=auth_headers)
    assert created.status_code == 201
    order = created.json()["order"]
    assert order["status"] == "pending"
    assert order["total_amount"] == "14.98"
    assert len(order["items"]) == 2

    history = await client.get("/api/v1/orders/", headers=auth_headers)
    assert history.status_code == 200
    assert len(history.json()["orders"]) == 1

    canceled = await client.post(
        f"/api/v1/orders/{order['id']}/cancel",
        headers=auth_headers,
    )
    assert canceled.status_code == 200

    history_after_cancel = await client.get(
        "/api/v1/orders/",
        headers=auth_headers,
    )
    assert history_after_cancel.json()["orders"][0]["status"] == "canceled"


async def test_create_order_rejects_empty_cart(
    client: AsyncClient,
    active_user: UserModel,
    auth_headers: dict[str, str],
) -> None:
    response = await client.post("/api/v1/orders/", headers=auth_headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "The cart is empty."


async def test_create_order_excludes_purchased_movie(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
    active_user: UserModel,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    purchased_movie, available_movie = seeded_movies[:2]
    await add_to_cart(client, purchased_movie, auth_headers)
    await add_to_cart(client, available_movie, auth_headers)

    db_session.add(
        OrderModel(
            user_id=active_user.id,
            status=OrderStatusEnum.PAID,
            total_amount=purchased_movie.price,
            items=[
                OrderItemModel(
                    movie_id=purchased_movie.id,
                    price_at_order=purchased_movie.price,
                )
            ],
        )
    )
    await db_session.commit()

    response = await client.post("/api/v1/orders/", headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["order"]["total_amount"] == "8.99"
    assert data["order"]["items"][0]["movie"]["name"] == available_movie.name
    assert data["excluded_movies"] == [
        {
            "uuid": str(purchased_movie.uuid),
            "name": purchased_movie.name,
            "reason": "Movie has already been purchased.",
        }
    ]


async def test_pending_movie_cannot_be_ordered_twice(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
    auth_headers: dict[str, str],
) -> None:
    await add_to_cart(client, seeded_movies[0], auth_headers)
    first_order = await client.post("/api/v1/orders/", headers=auth_headers)
    second_order = await client.post("/api/v1/orders/", headers=auth_headers)

    assert first_order.status_code == 201
    assert second_order.status_code == 409
    assert second_order.json()["detail"]["message"] == (
        "No movies are available to order."
    )


async def test_paid_order_requires_refund_instead_of_cancellation(
    client: AsyncClient,
    active_user: UserModel,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    order = OrderModel(
        user_id=active_user.id,
        status=OrderStatusEnum.PAID,
        total_amount=Decimal("5.00"),
        items=[],
    )
    db_session.add(order)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/orders/{order.id}/cancel",
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert "refund request" in response.json()["detail"]


async def test_cart_and_orders_require_authentication(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
) -> None:
    cart_response = await client.get("/api/v1/cart/")
    order_response = await client.get("/api/v1/orders/")

    assert cart_response.status_code == 401
    assert order_response.status_code == 401
