from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from database.models import (
    MovieModel,
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
