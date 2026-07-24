from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from database.models import OrderStatusEnum


class OrderMovieSchema(BaseModel):
    uuid: UUID
    name: str

    model_config = {"from_attributes": True}


class OrderItemSchema(BaseModel):
    id: int
    price_at_order: Decimal
    movie: OrderMovieSchema

    model_config = {"from_attributes": True}


class OrderSchema(BaseModel):
    id: int
    created_at: datetime
    status: OrderStatusEnum
    total_amount: Decimal | None
    items: list[OrderItemSchema]

    model_config = {"from_attributes": True}


class OrderListSchema(BaseModel):
    orders: list[OrderSchema]


class ExcludedMovieSchema(BaseModel):
    uuid: UUID
    name: str
    reason: str


class OrderCreateResponseSchema(BaseModel):
    order: OrderSchema
    excluded_movies: list[ExcludedMovieSchema]
