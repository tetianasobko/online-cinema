from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any, TypedDict

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import get_stripe_gateway
from database.models import (
    CartItemModel,
    MovieModel,
    OrderModel,
    OrderStatusEnum,
    PaymentModel,
    PaymentStatusEnum,
    UserModel,
)
from main import app
from payments import (
    InvalidWebhookSignatureError,
    StripeCheckoutSession,
    StripeGatewayInterface,
    StripeRefund,
)
from tests.doubles.stubs import StubEmailSender

pytestmark = pytest.mark.integration


class CheckoutRequest(TypedDict):
    line_items: Sequence[Mapping[str, Any]]
    success_url: str
    cancel_url: str
    metadata: Mapping[str, str]


class FakeStripeGateway(StripeGatewayInterface):
    def __init__(self) -> None:
        self.checkout_requests: list[CheckoutRequest] = []
        self.event: Mapping[str, Any] = {}
        self.refund = StripeRefund(id="re_test", status="pending")

    async def create_checkout_session(
        self,
        *,
        line_items: Sequence[Mapping[str, Any]],
        success_url: str,
        cancel_url: str,
        metadata: Mapping[str, str],
    ) -> StripeCheckoutSession:
        self.checkout_requests.append(
            {
                "line_items": line_items,
                "success_url": success_url,
                "cancel_url": cancel_url,
                "metadata": metadata,
            }
        )
        return StripeCheckoutSession(
            id="cs_test_checkout",
            url="https://checkout.stripe.test/session",
        )

    async def retrieve_checkout_session(
        self,
        session_id: str,
    ) -> Mapping[str, Any]:
        return {
            "id": session_id,
            "status": "open",
            "metadata": {"order_id": "1", "user_id": "1"},
        }

    async def expire_checkout_session(
        self,
        session_id: str,
    ) -> Mapping[str, Any]:
        return {"id": session_id, "status": "expired"}

    async def create_refund(
        self,
        checkout_session_id: str,
    ) -> StripeRefund:
        return self.refund

    def construct_webhook_event(
        self,
        *,
        payload: bytes,
        signature: str,
    ) -> Mapping[str, Any]:
        if signature != "valid-signature":
            raise InvalidWebhookSignatureError(
                "Invalid Stripe webhook signature."
            )
        return self.event


@pytest.fixture
def stripe_gateway() -> FakeStripeGateway:
    gateway = FakeStripeGateway()
    app.dependency_overrides[get_stripe_gateway] = lambda: gateway
    return gateway


async def create_pending_order(
    client: AsyncClient,
    movie: MovieModel,
    auth_headers: dict[str, str],
) -> dict[str, Any]:
    add_response = await client.post(
        f"/api/v1/cart/{movie.uuid}",
        headers=auth_headers,
    )
    assert add_response.status_code == 201

    order_response = await client.post(
        "/api/v1/orders/",
        headers=auth_headers,
    )
    assert order_response.status_code == 201
    return order_response.json()["order"]


def checkout_event(
    *,
    event_type: str,
    session_id: str,
    order_id: int,
    user_id: int,
    amount: int,
    payment_status: str = "paid",
) -> dict[str, Any]:
    return {
        "type": event_type,
        "data": {
            "object": {
                "id": session_id,
                "payment_status": payment_status,
                "amount_total": amount,
                "metadata": {
                    "order_id": str(order_id),
                    "user_id": str(user_id),
                },
            }
        },
    }


async def test_checkout_revalidates_total_and_returns_stripe_url(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
    auth_headers: dict[str, str],
    stripe_gateway: FakeStripeGateway,
    db_session: AsyncSession,
) -> None:
    movie = seeded_movies[0]
    order = await create_pending_order(client, movie, auth_headers)
    movie.price = Decimal("6.49")
    await db_session.commit()

    response = await client.post(
        "/api/v1/payments/checkout",
        json={"order_id": order["id"]},
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert response.json() == {
        "checkout_session_id": "cs_test_checkout",
        "checkout_url": "https://checkout.stripe.test/session",
    }
    request = stripe_gateway.checkout_requests[0]
    assert request["metadata"] == {
        "order_id": str(order["id"]),
        "user_id": "1",
    }
    assert request["line_items"][0]["price_data"]["unit_amount"] == 649

    refreshed_order = await db_session.get(OrderModel, order["id"])
    assert refreshed_order is not None
    assert refreshed_order.total_amount == Decimal("6.49")


async def test_checkout_rejects_unknown_order_and_anonymous_user(
    client: AsyncClient,
    auth_headers: dict[str, str],
    stripe_gateway: FakeStripeGateway,
) -> None:
    missing = await client.post(
        "/api/v1/payments/checkout",
        json={"order_id": 9999},
        headers=auth_headers,
    )
    anonymous = await client.post(
        "/api/v1/payments/checkout",
        json={"order_id": 1},
    )

    assert missing.status_code == 404
    assert missing.json()["detail"] == "Order not found."
    assert anonymous.status_code == 401


async def test_successful_webhook_creates_payment_and_fulfills_order(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
    active_user: UserModel,
    auth_headers: dict[str, str],
    stripe_gateway: FakeStripeGateway,
    db_session: AsyncSession,
    email_sender_stub: StubEmailSender,
) -> None:
    movie = seeded_movies[0]
    order = await create_pending_order(client, movie, auth_headers)
    stripe_gateway.event = checkout_event(
        event_type="checkout.session.completed",
        session_id="cs_success",
        order_id=order["id"],
        user_id=active_user.id,
        amount=599,
    )

    response = await client.post(
        "/api/v1/payments/webhook",
        content=b"stripe payload",
        headers={"stripe-signature": "valid-signature"},
    )

    assert response.status_code == 200
    assert response.json()["processed"] is True
    assert response.json()["payment_id"] is not None

    payment = await db_session.scalar(
        select(PaymentModel)
        .options(selectinload(PaymentModel.items))
        .where(PaymentModel.external_payment_id == "cs_success")
    )
    assert payment is not None
    assert payment.status == PaymentStatusEnum.SUCCESSFUL
    assert payment.amount == Decimal("5.99")
    assert len(payment.items) == 1

    refreshed_order = await db_session.get(OrderModel, order["id"])
    assert refreshed_order is not None
    assert refreshed_order.status == OrderStatusEnum.PAID
    assert await db_session.scalar(select(CartItemModel.id)) is None
    assert email_sender_stub.payment_confirmation_emails[0][
        "recipient"
    ] == active_user.email


async def test_webhook_is_idempotent(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
    active_user: UserModel,
    auth_headers: dict[str, str],
    stripe_gateway: FakeStripeGateway,
    db_session: AsyncSession,
    email_sender_stub: StubEmailSender,
) -> None:
    order = await create_pending_order(
        client,
        seeded_movies[0],
        auth_headers,
    )
    stripe_gateway.event = checkout_event(
        event_type="checkout.session.completed",
        session_id="cs_repeated",
        order_id=order["id"],
        user_id=active_user.id,
        amount=599,
    )
    headers = {"stripe-signature": "valid-signature"}

    first = await client.post(
        "/api/v1/payments/webhook",
        content=b"payload",
        headers=headers,
    )
    second = await client.post(
        "/api/v1/payments/webhook",
        content=b"payload",
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["payment_id"] == second.json()["payment_id"]
    payments = list((await db_session.scalars(select(PaymentModel))).all())
    assert len(payments) == 1
    assert len(email_sender_stub.payment_confirmation_emails) == 1


async def test_failed_webhook_creates_canceled_payment(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
    active_user: UserModel,
    auth_headers: dict[str, str],
    stripe_gateway: FakeStripeGateway,
    db_session: AsyncSession,
) -> None:
    order = await create_pending_order(
        client,
        seeded_movies[0],
        auth_headers,
    )
    stripe_gateway.event = checkout_event(
        event_type="checkout.session.async_payment_failed",
        session_id="cs_failed",
        order_id=order["id"],
        user_id=active_user.id,
        amount=599,
    )

    response = await client.post(
        "/api/v1/payments/webhook",
        content=b"payload",
        headers={"stripe-signature": "valid-signature"},
    )

    assert response.status_code == 200
    payment = await db_session.scalar(
        select(PaymentModel).where(
            PaymentModel.external_payment_id == "cs_failed"
        )
    )
    assert payment is not None
    assert payment.status == PaymentStatusEnum.CANCELED
    refreshed_order = await db_session.get(OrderModel, order["id"])
    assert refreshed_order is not None
    assert refreshed_order.status == OrderStatusEnum.PENDING


async def test_webhook_rejects_missing_signature_and_amount_mismatch(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
    active_user: UserModel,
    auth_headers: dict[str, str],
    stripe_gateway: FakeStripeGateway,
) -> None:
    order = await create_pending_order(
        client,
        seeded_movies[0],
        auth_headers,
    )
    missing_signature = await client.post(
        "/api/v1/payments/webhook",
        content=b"payload",
    )

    stripe_gateway.event = checkout_event(
        event_type="checkout.session.completed",
        session_id="cs_wrong_amount",
        order_id=order["id"],
        user_id=active_user.id,
        amount=100,
    )
    mismatch = await client.post(
        "/api/v1/payments/webhook",
        content=b"payload",
        headers={"stripe-signature": "valid-signature"},
    )

    assert missing_signature.status_code == 400
    assert mismatch.status_code == 409
    assert "does not match" in mismatch.json()["detail"]


async def test_payment_history_and_success_result(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
    active_user: UserModel,
    auth_headers: dict[str, str],
    stripe_gateway: FakeStripeGateway,
) -> None:
    order = await create_pending_order(
        client,
        seeded_movies[0],
        auth_headers,
    )
    stripe_gateway.event = checkout_event(
        event_type="checkout.session.completed",
        session_id="cs_history",
        order_id=order["id"],
        user_id=active_user.id,
        amount=599,
    )
    await client.post(
        "/api/v1/payments/webhook",
        content=b"payload",
        headers={"stripe-signature": "valid-signature"},
    )

    history = await client.get(
        "/api/v1/payments/",
        headers=auth_headers,
    )
    result = await client.get(
        "/api/v1/payments/success",
        params={"session_id": "cs_history"},
    )

    assert history.status_code == 200
    assert history.json()["payments"][0]["amount"] == "5.99"
    assert history.json()["payments"][0]["status"] == "successful"
    assert result.status_code == 200
    assert result.json()["status"] == "successful"


async def test_successful_payment_can_request_refund(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
    active_user: UserModel,
    auth_headers: dict[str, str],
    stripe_gateway: FakeStripeGateway,
) -> None:
    order = await create_pending_order(
        client,
        seeded_movies[0],
        auth_headers,
    )
    stripe_gateway.event = checkout_event(
        event_type="checkout.session.completed",
        session_id="cs_refund",
        order_id=order["id"],
        user_id=active_user.id,
        amount=599,
    )
    webhook = await client.post(
        "/api/v1/payments/webhook",
        content=b"payload",
        headers={"stripe-signature": "valid-signature"},
    )

    response = await client.post(
        f"/api/v1/payments/{webhook.json()['payment_id']}/refund",
        headers=auth_headers,
    )

    assert response.status_code == 202
    assert response.json()["refund_id"] == "re_test"
    assert response.json()["status"] == "processing"
