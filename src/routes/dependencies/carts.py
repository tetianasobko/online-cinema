from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import CartItemModel, CartModel, MovieModel, UserModel
from database.session import get_db
from security.authorization import get_current_user


async def get_or_create_cart(
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CartModel:
    cart = await db.scalar(
        select(CartModel)
        .options(
            selectinload(CartModel.items)
            .selectinload(CartItemModel.movie)
            .selectinload(MovieModel.genres)
        )
        .where(CartModel.user_id == user.id)
    )
    if cart is not None:
        return cart

    cart = CartModel(user_id=user.id, items=[])
    db.add(cart)
    await db.commit()
    return cart
