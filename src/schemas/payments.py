from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

from database.models import PaymentStatusEnum


class PaymentCreateSchema(BaseModel):
    order_id: int = Field(gt=0)


class PaymentCancellationSchema(BaseModel):
    checkout_session_id: str = Field(min_length=1, max_length=255)


class AdminPaymentFilterSchema(BaseModel):
    user_id: int | None = Field(default=None, gt=0)
    status: PaymentStatusEnum | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)

    @field_validator("created_from", "created_to")
    @classmethod
    def validate_timezone(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("Payment date filters must include a timezone.")
        return value

    @model_validator(mode="after")
    def validate_date_range(self) -> Self:
        if (
            self.created_from is not None
            and self.created_to is not None
            and self.created_from > self.created_to
        ):
            raise ValueError(
                "created_from cannot be later than created_to."
            )
        return self


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


class AdminPaymentSchema(PaymentSchema):
    user_id: int


class AdminPaymentListSchema(BaseModel):
    payments: list[AdminPaymentSchema]
    page: int
    per_page: int
    total_pages: int
    total_items: int


class PaymentCheckoutResponseSchema(BaseModel):
    checkout_session_id: str
    checkout_url: str


class PaymentRefundResponseSchema(BaseModel):
    refund_id: str
    status: str
    message: str


class PaymentWebhookResponseSchema(BaseModel):
    status: str
    processed: bool
    payment_id: int | None


class PaymentResultResponseSchema(BaseModel):
    status: str
    message: str
