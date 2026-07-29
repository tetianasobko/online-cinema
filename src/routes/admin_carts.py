from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import CartItemModel, CartModel, MovieModel, UserModel
from database.session import get_db
from routes.helpers import build_cart_items_and_total
from schemas.carts import AdminCartSchema
from security.authorization import require_admin


router = APIRouter(dependencies=[Depends(require_admin)])


@router.get(
    "/users/{user_id}/cart",
    response_model=AdminCartSchema,
    status_code=status.HTTP_200_OK,
    summary="Inspect a user's cart",
    description="Allow an administrator to view the contents of a user's cart.",
    responses={
        401: {"description": "Authentication is required."},
        403: {"description": "Administrator access is required."},
        404: {"description": "The user was not found."},
    },
)
async def get_user_cart(
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> AdminCartSchema:
    user = await db.get(UserModel, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    cart = await db.scalar(
        select(CartModel)
        .options(
            selectinload(CartModel.items)
            .selectinload(CartItemModel.movie)
            .selectinload(MovieModel.genres)
        )
        .where(CartModel.user_id == user.id)
    )
    if cart is None:
        return AdminCartSchema(
            user_id=user.id,
            user_email=user.email,
            cart_id=None,
            items=[],
            total_items=0,
            total_price=Decimal("0.00"),
        )

    items, total_price = build_cart_items_and_total(cart)
    return AdminCartSchema(
        user_id=user.id,
        user_email=user.email,
        cart_id=cart.id,
        items=items,
        total_items=len(items),
        total_price=total_price,
    )
