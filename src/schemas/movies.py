from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class MovieRelatedItemSchema(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class MovieListItemSchema(BaseModel):
    uuid: UUID
    name: str
    year: int
    time: int
    imdb: float
    votes: int
    price: Decimal | None
    genres: list[MovieRelatedItemSchema]

    model_config = {"from_attributes": True}


class MovieListResponseSchema(BaseModel):
    movies: list[MovieListItemSchema]
    page: int
    per_page: int
    total_pages: int
    total_items: int


class MovieDetailSchema(MovieListItemSchema):
    meta_score: float | None
    gross: float | None
    description: str
    certification: MovieRelatedItemSchema
    directors: list[MovieRelatedItemSchema]
    stars: list[MovieRelatedItemSchema]
