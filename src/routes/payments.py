from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import get_stripe_gateway, get_stripe_payment_service
from database.models import PaymentModel, PaymentStatusEnum, UserModel
from database.session import get_db
from payments import (
    InvalidWebhookEventError,
    InvalidWebhookPayloadError,
    InvalidWebhookSignatureError,
    OrderItemUnavailableError,
    OrderNotPayableError,
    PaymentAmountMismatchError,
    PaymentOrderNotFoundError,
    StripeCheckoutError,
    StripeGatewayInterface,
    StripePaymentService,
)
from schemas.payments import (
    PaymentCheckoutResponseSchema,
    PaymentCreateSchema,
    PaymentListSchema,
    PaymentResultResponseSchema,
    PaymentSchema,
    PaymentWebhookResponseSchema,
)
from security.authorization import get_current_user


router = APIRouter()


@router.get(
    "/success",
    response_model=PaymentResultResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_payment_result(
    session_id: str = Query(min_length=1, max_length=255),
    db: AsyncSession = Depends(get_db),
) -> PaymentResultResponseSchema:
    payment_status = await db.scalar(
        select(PaymentModel.status).where(
            PaymentModel.external_payment_id == session_id
        )
    )
    if payment_status is None:
        return PaymentResultResponseSchema(
            status="processing",
            message=(
                "Your payment is still being processed. "
                "Please check your payment history shortly."
            ),
        )

    messages = {
        PaymentStatusEnum.SUCCESSFUL: "Payment completed successfully.",
        PaymentStatusEnum.CANCELED: (
            "Payment was not completed. Try a different payment method."
        ),
        PaymentStatusEnum.REFUNDED: "Payment has been refunded.",
    }
    return PaymentResultResponseSchema(
        status=payment_status.value,
        message=messages[payment_status],
    )


@router.get(
    "/",
    response_model=PaymentListSchema,
    status_code=status.HTTP_200_OK,
)
async def get_payment_history(
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentListSchema:
    payments = list(
        (
            await db.scalars(
                select(PaymentModel)
                .options(selectinload(PaymentModel.items))
                .where(PaymentModel.user_id == user.id)
                .order_by(
                    PaymentModel.created_at.desc(),
                    PaymentModel.id.desc(),
                )
            )
        ).all()
    )
    return PaymentListSchema(
        payments=[
            PaymentSchema.model_validate(payment)
            for payment in payments
        ]
    )


@router.post(
    "/webhook",
    response_model=PaymentWebhookResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    gateway: StripeGatewayInterface = Depends(get_stripe_gateway),
    payment_service: StripePaymentService = Depends(
        get_stripe_payment_service
    ),
) -> PaymentWebhookResponseSchema:
    signature = request.headers.get("stripe-signature")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe-Signature header is missing.",
        )

    payload = await request.body()
    try:
        event = gateway.construct_webhook_event(
            payload=payload,
            signature=signature,
        )
        payment = await payment_service.process_webhook_event(
            db=db,
            event=event,
        )
    except (
        InvalidWebhookPayloadError,
        InvalidWebhookSignatureError,
        InvalidWebhookEventError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except PaymentOrderNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (PaymentAmountMismatchError, OrderNotPayableError) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return PaymentWebhookResponseSchema(
        status="success",
        processed=payment is not None,
        payment_id=payment.id if payment is not None else None,
    )


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
