from urllib.parse import parse_qs, urlsplit

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import MovieModel
from tests.doubles.stubs import StubEmailSender

pytestmark = pytest.mark.functional

EMAIL = "journey-user@example.com"
PASSWORD = "StrongJourneyPassword123"


async def register_activate_and_login(
    client: AsyncClient,
    email_sender: StubEmailSender,
) -> dict[str, str]:
    registration = await client.post(
        "/api/v1/accounts/register",
        json={"email": EMAIL, "password": PASSWORD},
    )
    assert registration.status_code == 201
    assert registration.json()["is_active"] is False

    assert len(email_sender.activation_emails) == 1
    recipient, activation_link = email_sender.activation_emails[0]
    assert recipient == EMAIL
    activation_query = parse_qs(urlsplit(activation_link).query)

    activation = await client.get(
        "/api/v1/accounts/activate",
        params={
            "email": activation_query["email"][0],
            "token": activation_query["token"][0],
        },
    )
    assert activation.status_code == 200

    login = await client.post(
        "/api/v1/accounts/login",
        json={"email": EMAIL, "password": PASSWORD},
    )
    assert login.status_code == 201
    assert login.json()["access_token"]
    assert login.json()["refresh_token"]
    return {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }


async def test_registration_activation_and_login_journey(
    client: AsyncClient,
    seeded_user_groups: AsyncSession,
    email_sender_stub: StubEmailSender,
) -> None:
    headers = await register_activate_and_login(
        client,
        email_sender_stub,
    )

    protected_response = await client.get(
        "/api/v1/favorites/",
        headers=headers,
    )

    assert protected_response.status_code == 200
    assert protected_response.json()["movies"] == []


async def test_movie_discovery_to_order_placement_journey(
    client: AsyncClient,
    seeded_user_groups: AsyncSession,
    seeded_movies: list[MovieModel],
    email_sender_stub: StubEmailSender,
) -> None:
    headers = await register_activate_and_login(
        client,
        email_sender_stub,
    )

    catalog = await client.get(
        "/api/v1/movies/",
        params={
            "search": "journey",
            "year": 2020,
            "imdb_min": 8,
            "sort_by": "price",
            "sort_order": "asc",
        },
    )
    assert catalog.status_code == 200
    assert catalog.json()["total_items"] == 1
    movie = catalog.json()["movies"][0]
    assert movie["name"] == "Alpha Journey"

    details = await client.get(f"/api/v1/movies/{movie['uuid']}")
    assert details.status_code == 200
    assert details.json()["description"]

    add_to_cart = await client.post(
        f"/api/v1/cart/{movie['uuid']}",
        headers=headers,
    )
    assert add_to_cart.status_code == 201

    cart = await client.get("/api/v1/cart/", headers=headers)
    assert cart.status_code == 200
    assert cart.json()["total_items"] == 1
    assert cart.json()["total_price"] == "5.99"

    placed_order = await client.post(
        "/api/v1/orders/",
        headers=headers,
    )
    assert placed_order.status_code == 201
    order = placed_order.json()["order"]
    assert order["status"] == "pending"
    assert order["total_amount"] == "5.99"
    assert order["items"][0]["movie"]["name"] == "Alpha Journey"

    order_history = await client.get(
        "/api/v1/orders/",
        headers=headers,
    )
    assert order_history.status_code == 200
    assert len(order_history.json()["orders"]) == 1
    assert order_history.json()["orders"][0]["id"] == order["id"]
