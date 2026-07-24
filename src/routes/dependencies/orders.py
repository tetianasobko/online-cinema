from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import OrderModel, UserModel
from database.session import get_db
from security.authorization import get_current_user


async def get_user_order_or_404(
    order_id: int,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderModel:
    order = await db.scalar(
        select(OrderModel).where(
            OrderModel.id == order_id,
            OrderModel.user_id == user.id,
        )
    )
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )
    return order
