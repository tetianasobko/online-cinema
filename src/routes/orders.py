from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import (
    CartItemModel,
    CartModel,
    OrderItemModel,
    OrderModel,
    OrderStatusEnum,
    UserModel,
)
from database.session import get_db
from routes.dependencies import get_or_create_cart
from schemas.orders import (
    ExcludedMovieSchema,
    OrderCreateResponseSchema,
    OrderListSchema,
    OrderSchema,
)
from security.authorization import get_current_user


router = APIRouter()


@router.get(
    "/",
    response_model=OrderListSchema,
    status_code=status.HTTP_200_OK,
)
async def get_orders(
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderListSchema:
    orders = list(
        (
            await db.scalars(
                select(OrderModel)
                .options(
                    selectinload(OrderModel.items).selectinload(
                        OrderItemModel.movie
                    )
                )
                .where(OrderModel.user_id == user.id)
                .order_by(OrderModel.created_at.desc(), OrderModel.id.desc())
            )
        ).all()
    )
    return OrderListSchema(
        orders=[OrderSchema.model_validate(order) for order in orders]
    )


@router.post(
    "/",
    response_model=OrderCreateResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_order(
    user: UserModel = Depends(get_current_user),
    cart: CartModel = Depends(get_or_create_cart),
    db: AsyncSession = Depends(get_db),
) -> OrderCreateResponseSchema:
    if not cart.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The cart is empty.",
        )

    movie_ids = [cart_item.movie_id for cart_item in cart.items]
    existing_order_rows = (
        await db.execute(
            select(OrderItemModel.movie_id, OrderModel.status)
            .join(OrderModel)
            .where(
                OrderModel.user_id == user.id,
                OrderItemModel.movie_id.in_(movie_ids),
                OrderModel.status.in_(
                    [OrderStatusEnum.PAID, OrderStatusEnum.PENDING]
                ),
            )
        )
    ).all()
    purchased_movie_ids = {
        movie_id
        for movie_id, order_status in existing_order_rows
        if order_status == OrderStatusEnum.PAID
    }
    pending_movie_ids = {
        movie_id
        for movie_id, order_status in existing_order_rows
        if order_status == OrderStatusEnum.PENDING
    }

    valid_cart_items = []
    excluded_movies = []
    excluded_cart_item_ids = []
    for cart_item in cart.items:
        movie = cart_item.movie
        if movie.price is None:
            reason = "Movie is not available for purchase."
        elif movie.id in purchased_movie_ids:
            reason = "Movie has already been purchased."
        elif movie.id in pending_movie_ids:
            reason = "Movie is already included in a pending order."
        else:
            reason = None

        if reason is None:
            valid_cart_items.append(cart_item)
            continue

        excluded_cart_item_ids.append(cart_item.id)
        excluded_movies.append(
            ExcludedMovieSchema(
                uuid=movie.uuid,
                name=movie.name,
                reason=reason,
            )
        )

    if excluded_cart_item_ids:
        await db.execute(
            delete(CartItemModel).where(
                CartItemModel.id.in_(excluded_cart_item_ids)
            )
        )

    if not valid_cart_items:
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "No movies are available to order.",
                "excluded_movies": [
                    movie.model_dump(mode="json")
                    for movie in excluded_movies
                ],
            },
        )

    total_amount = Decimal("0.00")
    order_items = []
    for cart_item in valid_cart_items:
        price = cart_item.movie.price
        if price is None:
            continue
        total_amount += price
        order_items.append(
            OrderItemModel(
                movie=cart_item.movie,
                price_at_order=price,
            )
        )

    order = OrderModel(
        user_id=user.id,
        status=OrderStatusEnum.PENDING,
        total_amount=total_amount,
        items=order_items,
    )
    db.add(order)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The cart changed while the order was being created.",
        ) from error

    return OrderCreateResponseSchema(
        order=OrderSchema.model_validate(order),
        excluded_movies=excluded_movies,
    )
