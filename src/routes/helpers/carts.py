from decimal import Decimal

from database.models import CartModel
from schemas.carts import CartItemSchema


def build_cart_items_and_total(
    cart: CartModel,
) -> tuple[list[CartItemSchema], Decimal]:
    items = [
        CartItemSchema.model_validate(item)
        for item in cart.items
    ]
    total_price = sum(
        (
            item.movie.price
            for item in cart.items
            if item.movie.price is not None
        ),
        start=Decimal("0.00"),
    )
    return items, total_price
