from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_stripe_payment_service
from database.models import UserModel
from database.session import get_db
from payments import (
    OrderItemUnavailableError,
    OrderNotPayableError,
    PaymentOrderNotFoundError,
    StripeCheckoutError,
    StripePaymentService,
)
from schemas.payments import (
    PaymentCheckoutResponseSchema,
    PaymentCreateSchema,
)
from security.authorization import get_current_user


router = APIRouter()


@router.post(
    "/checkout",
    response_model=PaymentCheckoutResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_checkout(
    data: PaymentCreateSchema,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    payment_service: StripePaymentService = Depends(
        get_stripe_payment_service
    ),
) -> PaymentCheckoutResponseSchema:
    try:
        checkout = await payment_service.create_checkout_session(
            db=db,
            user=user,
            order_id=data.order_id,
        )
    except PaymentOrderNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (OrderNotPayableError, OrderItemUnavailableError) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except StripeCheckoutError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error

    return PaymentCheckoutResponseSchema(
        checkout_session_id=checkout.id,
        checkout_url=checkout.url,
    )
