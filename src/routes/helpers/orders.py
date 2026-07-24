from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import MovieModel, OrderModel


async def revalidate_order_total(
    db: AsyncSession,
    order: OrderModel,
) -> Decimal:
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
            raise ValueError(
                f"Movie with ID {item.movie_id} no longer exists."
            )

        current_price = current_prices[item.movie_id]
        if current_price is None:
            raise ValueError(
                f"Movie with ID {item.movie_id} is unavailable for purchase."
            )

        item.price_at_order = current_price
        total_amount += current_price

    order.total_amount = total_amount
    return total_amount
