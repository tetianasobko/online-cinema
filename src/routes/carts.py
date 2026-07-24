from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    CartItemModel,
    CartModel,
    MovieModel,
    OrderItemModel,
    OrderModel,
    OrderStatusEnum,
)
from database.session import get_db
from routes.dependencies import (
    get_movie_id_or_404,
    get_movie_or_404,
    get_or_create_cart,
)
from schemas.accounts import MessageResponseSchema
from schemas.carts import CartItemSchema, CartSchema


router = APIRouter()


@router.post(
    "/{movie_uuid}",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def add_movie_to_cart(
    movie_uuid: UUID,
    cart: CartModel = Depends(get_or_create_cart),
    db: AsyncSession = Depends(get_db),
) -> MessageResponseSchema:
    movie: MovieModel = await get_movie_or_404(movie_uuid, db)
    if movie.price is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This movie is not available for purchase.",
        )

    purchased_item_id = await db.scalar(
        select(OrderItemModel.id)
        .join(OrderModel)
        .where(
            OrderModel.user_id == cart.user_id,
            OrderModel.status == OrderStatusEnum.PAID,
            OrderItemModel.movie_id == movie.id,
        )
    )
    if purchased_item_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This movie has already been purchased. "
                "Repeat purchases are not allowed."
            ),
        )

    existing_item_id = await db.scalar(
        select(CartItemModel.id).where(
            CartItemModel.cart_id == cart.id,
            CartItemModel.movie_id == movie.id,
        )
    )
    if existing_item_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This movie is already in the cart.",
        )

    db.add(CartItemModel(cart_id=cart.id, movie_id=movie.id))
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This movie is already in the cart.",
        ) from error

    return MessageResponseSchema(message="Movie added to the cart.")


@router.delete(
    "/{movie_uuid}",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def remove_movie_from_cart(
    movie_id: int = Depends(get_movie_id_or_404),
    cart: CartModel = Depends(get_or_create_cart),
    db: AsyncSession = Depends(get_db),
) -> MessageResponseSchema:
    cart_item = await db.scalar(
        select(CartItemModel).where(
            CartItemModel.cart_id == cart.id,
            CartItemModel.movie_id == movie_id,
        )
    )
    if cart_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This movie is not in the cart.",
        )

    await db.delete(cart_item)
    await db.commit()
    return MessageResponseSchema(message="Movie removed from the cart.")


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
