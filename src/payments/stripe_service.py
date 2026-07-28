from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from database.models import (
    CartItemModel,
    CartModel,
    MovieModel,
    OrderItemModel,
    OrderModel,
    OrderStatusEnum,
    PaymentItemModel,
    PaymentModel,
    PaymentStatusEnum,
    UserModel,
)
from payments.exceptions import (
    InvalidWebhookEventError,
    OrderItemUnavailableError,
    OrderNotPayableError,
    PaymentAmountMismatchError,
    PaymentOrderNotFoundError,
)
from payments.interfaces import (
    PaymentEmailConfirmation,
    StripeCheckoutSession,
    StripeGatewayInterface,
    WebhookProcessingResult,
)


class StripePaymentService:
    _SUCCESSFUL_EVENTS = {
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
    }
    _FAILED_EVENTS = {
        "checkout.session.async_payment_failed",
        "checkout.session.expired",
    }

    def __init__(
        self,
        gateway: StripeGatewayInterface,
        *,
        success_url: str,
        cancel_url: str,
        currency: str,
    ) -> None:
        self._gateway = gateway
        self._success_url = success_url
        self._cancel_url = cancel_url
        self._currency = currency.lower()

    async def create_checkout_session(
        self,
        *,
        db: AsyncSession,
        user: UserModel,
        order_id: int,
    ) -> StripeCheckoutSession:
        order = await db.scalar(
            select(OrderModel)
            .options(
                selectinload(OrderModel.items).joinedload(
                    OrderItemModel.movie
                )
            )
            .where(
                OrderModel.id == order_id,
                OrderModel.user_id == user.id,
            )
        )
        if order is None:
            raise PaymentOrderNotFoundError("Order not found.")
        if order.status != OrderStatusEnum.PENDING:
            raise OrderNotPayableError(
                "Only pending orders can be paid."
            )
        if not order.items:
            raise OrderNotPayableError("The order has no items.")

        await self._revalidate_order_total(db, order)

        line_items = []
        for item in order.items:
            movie = item.movie
            price = item.price_at_order
            unit_amount = self._to_minor_units(price)
            line_items.append(
                {
                    "price_data": {
                        "currency": self._currency,
                        "product_data": {"name": movie.name},
                        "unit_amount": unit_amount,
                    },
                    "quantity": 1,
                }
            )

        await db.commit()
        return await self._gateway.create_checkout_session(
            line_items=line_items,
            success_url=self._success_url,
            cancel_url=self._cancel_url,
            metadata={
                "order_id": str(order.id),
                "user_id": str(user.id),
            },
        )

    async def process_webhook_event(
        self,
        *,
        db: AsyncSession,
        event: Mapping[str, Any],
    ) -> WebhookProcessingResult:
        event_type = event.get("type")
        if (
            event_type not in self._SUCCESSFUL_EVENTS
            and event_type not in self._FAILED_EVENTS
        ):
            return WebhookProcessingResult(
                payment_id=None,
                processed=False,
                created=False,
            )

        session = self._get_webhook_session(event)
        if (
            event_type == "checkout.session.completed"
            and session.get("payment_status") != "paid"
        ):
            return WebhookProcessingResult(
                payment_id=None,
                processed=False,
                created=False,
            )

        session_id = session.get("id")
        if not isinstance(session_id, str) or not session_id:
            raise InvalidWebhookEventError(
                "Stripe Checkout Session ID is missing."
            )

        existing_payment = await db.scalar(
            select(PaymentModel)
            .options(selectinload(PaymentModel.items))
            .where(PaymentModel.external_payment_id == session_id)
        )
        if existing_payment is not None:
            return WebhookProcessingResult(
                payment_id=existing_payment.id,
                processed=True,
                created=False,
            )

        order_id, user_id = self._get_webhook_metadata(session)
        order = await db.scalar(
            select(OrderModel)
            .options(
                joinedload(OrderModel.user),
                selectinload(OrderModel.items).joinedload(
                    OrderItemModel.movie
                ),
            )
            .where(
                OrderModel.id == order_id,
                OrderModel.user_id == user_id,
            )
        )
        if order is None:
            raise PaymentOrderNotFoundError("Order not found.")
        if order.status == OrderStatusEnum.CANCELED:
            raise OrderNotPayableError("Canceled orders cannot be paid.")
        if not order.items or order.total_amount is None:
            raise OrderNotPayableError(
                "The order has no payable items."
            )

        stripe_amount = self._get_webhook_amount(session)
        if stripe_amount != order.total_amount:
            raise PaymentAmountMismatchError(
                "Stripe payment amount does not match the order total."
            )

        payment_status = (
            PaymentStatusEnum.SUCCESSFUL
            if event_type in self._SUCCESSFUL_EVENTS
            else PaymentStatusEnum.CANCELED
        )
        payment = PaymentModel(
            user_id=user_id,
            order_id=order.id,
            status=payment_status,
            amount=stripe_amount,
            external_payment_id=session_id,
            items=[
                PaymentItemModel(
                    order_item=item,
                    price_at_payment=item.price_at_order,
                )
                for item in order.items
            ],
        )
        db.add(payment)
        if payment_status == PaymentStatusEnum.SUCCESSFUL:
            order.status = OrderStatusEnum.PAID
            purchased_movie_ids = [item.movie_id for item in order.items]
            await db.execute(
                delete(CartItemModel).where(
                    CartItemModel.cart_id.in_(
                        select(CartModel.id).where(
                            CartModel.user_id == user_id
                        )
                    ),
                    CartItemModel.movie_id.in_(purchased_movie_ids),
                )
            )

        try:
            await db.commit()
        except IntegrityError as error:
            await db.rollback()
            raise InvalidWebhookEventError(
                "The Stripe payment could not be saved."
            ) from error

        email_confirmation = None
        if payment_status == PaymentStatusEnum.SUCCESSFUL:
            email_confirmation = PaymentEmailConfirmation(
                recipient=order.user.email,
                order_id=order.id,
                movie_names=tuple(
                    item.movie.name for item in order.items
                ),
                total_amount=payment.amount,
                currency=self._currency,
                payment_date=payment.created_at,
            )

        return WebhookProcessingResult(
            payment_id=payment.id,
            processed=True,
            created=True,
            email_confirmation=email_confirmation,
        )

    @staticmethod
    def _get_webhook_session(
        event: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        data = event.get("data")
        if not isinstance(data, Mapping):
            raise InvalidWebhookEventError(
                "Stripe webhook data is missing."
            )
        session = data.get("object")
        if not isinstance(session, Mapping):
            raise InvalidWebhookEventError(
                "Stripe Checkout Session is missing."
            )
        return session

    @staticmethod
    def _get_webhook_metadata(
        session: Mapping[str, Any],
    ) -> tuple[int, int]:
        metadata = session.get("metadata")
        if not isinstance(metadata, Mapping):
            raise InvalidWebhookEventError(
                "Stripe Checkout metadata is missing."
            )
        try:
            order_id = int(metadata["order_id"])
            user_id = int(metadata["user_id"])
        except (KeyError, TypeError, ValueError) as error:
            raise InvalidWebhookEventError(
                "Stripe Checkout metadata is invalid."
            ) from error
        if order_id <= 0 or user_id <= 0:
            raise InvalidWebhookEventError(
                "Stripe Checkout metadata is invalid."
            )
        return order_id, user_id

    @staticmethod
    def _get_webhook_amount(
        session: Mapping[str, Any],
    ) -> Decimal:
        amount_total = session.get("amount_total")
        if not isinstance(amount_total, int) or amount_total < 0:
            raise InvalidWebhookEventError(
                "Stripe payment amount is invalid."
            )
        return Decimal(amount_total) / 100

    @staticmethod
    async def _revalidate_order_total(
        db: AsyncSession,
        order: OrderModel,
    ) -> None:
        movie_ids = [item.movie_id for item in order.items]
        price_rows = await db.execute(
            select(MovieModel.id, MovieModel.price).where(
                MovieModel.id.in_(movie_ids)
            )
        )
        current_prices: dict[int, Decimal | None] = {
            movie_id: price
            for movie_id, price in price_rows.tuples()
        }

        total_amount = Decimal("0.00")
        for item in order.items:
            if item.movie_id not in current_prices:
                raise OrderItemUnavailableError(
                    f"Movie with ID {item.movie_id} no longer exists."
                )

            current_price = current_prices[item.movie_id]
            if current_price is None:
                raise OrderItemUnavailableError(
                    f"Movie with ID {item.movie_id} is unavailable for "
                    "purchase."
                )

            item.price_at_order = current_price
            total_amount += current_price

        order.total_amount = total_amount

    @staticmethod
    def _to_minor_units(amount: Decimal) -> int:
        minor_units = amount * 100
        if amount <= 0 or minor_units != minor_units.to_integral_value():
            raise OrderItemUnavailableError(
                "Movie price must be a positive amount with two decimals."
            )
        return int(minor_units)
