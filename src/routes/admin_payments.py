from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import PaymentModel
from database.session import get_db
from schemas.payments import (
    AdminPaymentFilterSchema,
    AdminPaymentListSchema,
    AdminPaymentSchema,
)
from security.authorization import require_admin


router = APIRouter(dependencies=[Depends(require_admin)])


@router.get(
    "/payments",
    response_model=AdminPaymentListSchema,
    status_code=status.HTTP_200_OK,
)
async def get_payments(
    params: Annotated[AdminPaymentFilterSchema, Query()],
    db: AsyncSession = Depends(get_db),
) -> AdminPaymentListSchema:
    filters = []
    if params.user_id is not None:
        filters.append(PaymentModel.user_id == params.user_id)
    if params.status is not None:
        filters.append(PaymentModel.status == params.status)
    if params.created_from is not None:
        filters.append(PaymentModel.created_at >= params.created_from)
    if params.created_to is not None:
        filters.append(PaymentModel.created_at <= params.created_to)

    total_items = (
        await db.scalar(
            select(func.count())
            .select_from(PaymentModel)
            .where(*filters)
        )
        or 0
    )
    payments = list(
        (
            await db.scalars(
                select(PaymentModel)
                .options(selectinload(PaymentModel.items))
                .where(*filters)
                .order_by(
                    PaymentModel.created_at.desc(),
                    PaymentModel.id.desc(),
                )
                .offset((params.page - 1) * params.per_page)
                .limit(params.per_page)
            )
        ).all()
    )

    return AdminPaymentListSchema(
        payments=[
            AdminPaymentSchema.model_validate(payment)
            for payment in payments
        ],
        page=params.page,
        per_page=params.per_page,
        total_pages=(
            ceil(total_items / params.per_page) if total_items else 0
        ),
        total_items=total_items,
    )
