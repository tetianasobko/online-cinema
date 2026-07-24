from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from schemas.movies import MovieRelatedItemSchema


class CartMovieSchema(BaseModel):
    uuid: UUID
    name: str
    price: Decimal | None
    year: int
    genres: list[MovieRelatedItemSchema]

    model_config = {"from_attributes": True}


class CartItemSchema(BaseModel):
    id: int
    added_at: datetime
    movie: CartMovieSchema

    model_config = {"from_attributes": True}


class CartSchema(BaseModel):
    id: int
    items: list[CartItemSchema]
    total_items: int
    total_price: Decimal

    model_config = {"from_attributes": True}
