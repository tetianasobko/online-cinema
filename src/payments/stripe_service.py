from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from database.models import (
    OrderItemModel,
    OrderModel,
    OrderStatusEnum,
    UserModel,
)
from payments.exceptions import (
    OrderItemUnavailableError,
    OrderNotPayableError,
    PaymentOrderNotFoundError,
)
from payments.interfaces import (
    StripeCheckoutSession,
    StripeGatewayInterface,
)
from routes.helpers import revalidate_order_total


class StripePaymentService:
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

        try:
            await revalidate_order_total(db, order)
        except ValueError as error:
            raise OrderItemUnavailableError(str(error)) from error

        line_items = []
        for item in order.items:
            movie = item.movie
            price = item.price_at_order
            if movie is None:
                raise OrderItemUnavailableError(
                    f"Movie with ID {item.movie_id} no longer exists."
                )

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

    @staticmethod
    def _to_minor_units(amount: Decimal) -> int:
        minor_units = amount * 100
        if amount <= 0 or minor_units != minor_units.to_integral_value():
            raise OrderItemUnavailableError(
                "Movie price must be a positive amount with two decimals."
            )
        return int(minor_units)
