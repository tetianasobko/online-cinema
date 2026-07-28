from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from database.models import PaymentStatusEnum


class PaymentCreateSchema(BaseModel):
    order_id: int = Field(gt=0)


class PaymentCancellationSchema(BaseModel):
    checkout_session_id: str = Field(min_length=1, max_length=255)


class PaymentItemSchema(BaseModel):
    id: int
    order_item_id: int
    price_at_payment: Decimal

    model_config = {"from_attributes": True}


class PaymentSchema(BaseModel):
    id: int
    order_id: int
    created_at: datetime
    status: PaymentStatusEnum
    amount: Decimal
    external_payment_id: str | None
    items: list[PaymentItemSchema]

    model_config = {"from_attributes": True}


class PaymentListSchema(BaseModel):
    payments: list[PaymentSchema]


class PaymentCheckoutResponseSchema(BaseModel):
    checkout_session_id: str
    checkout_url: str


class PaymentWebhookResponseSchema(BaseModel):
    status: str
    processed: bool
    payment_id: int | None


class PaymentResultResponseSchema(BaseModel):
    status: str
    message: str
