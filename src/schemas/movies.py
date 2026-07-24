from decimal import Decimal
from datetime import datetime
from enum import Enum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from database.models import MovieReactionEnum


class MovieSortField(str, Enum):
    PRICE = "price"
    YEAR = "year"
    IMDB = "imdb"
    POPULARITY = "popularity"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class MovieCatalogQuerySchema(BaseModel):
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=10, ge=1, le=20)
    year: int | None = Field(default=None, ge=1888)
    imdb_min: float | None = Field(default=None, ge=0, le=10)
    imdb_max: float | None = Field(default=None, ge=0, le=10)
    price_min: Decimal | None = Field(default=None, ge=0)
    price_max: Decimal | None = Field(default=None, ge=0)
    genre: str | None = Field(default=None, min_length=1)
    search: str | None = Field(default=None, min_length=1)
    sort_by: MovieSortField = MovieSortField.POPULARITY
    sort_order: SortOrder = SortOrder.DESC

    @model_validator(mode="after")
    def validate_ranges(self) -> Self:
        if (
            self.imdb_min is not None
            and self.imdb_max is not None
            and self.imdb_min > self.imdb_max
        ):
            raise ValueError("imdb_min cannot be greater than imdb_max.")
        if (
            self.price_min is not None
            and self.price_max is not None
            and self.price_min > self.price_max
        ):
            raise ValueError("price_min cannot be greater than price_max.")
        return self


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
    likes_count: int = 0
    dislikes_count: int = 0
    average_rating: float | None = None
    ratings_count: int = 0


class GenreWithMovieCountSchema(MovieRelatedItemSchema):
    movie_count: int


class MovieReactionRequestSchema(BaseModel):
    reaction: MovieReactionEnum


class MovieReactionResponseSchema(BaseModel):
    message: str
    reaction: MovieReactionEnum | None


class MovieRatingRequestSchema(BaseModel):
    rating: int = Field(ge=1, le=10)


class MovieRatingResponseSchema(BaseModel):
    message: str
    rating: int | None


class MovieCommentCreateSchema(BaseModel):
    text: str = Field(min_length=1, max_length=2000)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Comment text cannot be empty.")
        return text


class MovieCommentReplySchema(BaseModel):
    id: int
    text: str
    user_id: int
    parent_id: int
    created_at: datetime
    updated_at: datetime
    likes_count: int = 0

    model_config = {"from_attributes": True}


class MovieCommentSchema(BaseModel):
    id: int
    text: str
    user_id: int
    parent_id: int | None
    created_at: datetime
    updated_at: datetime
    likes_count: int = 0
    replies: list[MovieCommentReplySchema] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class MovieCommentListSchema(BaseModel):
    comments: list[MovieCommentSchema]
    page: int
    per_page: int
    total_pages: int
    total_items: int
