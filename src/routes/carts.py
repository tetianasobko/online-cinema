from decimal import Decimal

from fastapi import APIRouter, Depends, status

from database.models import CartModel
from routes.dependencies import get_or_create_cart
from schemas.carts import CartItemSchema, CartSchema


router = APIRouter()


@router.get(
    "/",
    response_model=CartSchema,
    status_code=status.HTTP_200_OK,
)
async def get_cart(
    cart: CartModel = Depends(get_or_create_cart),
) -> CartSchema:
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
    return CartSchema(
        id=cart.id,
        items=items,
        total_items=len(items),
        total_price=total_price,
    )
