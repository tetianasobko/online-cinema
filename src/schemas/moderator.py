from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from schemas.movies import MovieRelatedItemSchema


class GenreCreateSchema(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Genre name cannot be empty.")
        return value


class GenreUpdateSchema(GenreCreateSchema):
    pass


class GenreManagementSchema(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class MovieCreateSchema(BaseModel):
    name: str = Field(min_length=1, max_length=250)
    year: int = Field(ge=1888)
    time: int = Field(gt=0)
    imdb: float = Field(ge=0, le=10)
    votes: int = Field(ge=0)
    meta_score: float | None = Field(default=None, ge=0, le=100)
    gross: float | None = Field(default=None, ge=0)
    description: str = Field(min_length=1)
    price: Decimal | None = Field(default=None, ge=0)
    certification_id: int = Field(gt=0)
    genre_ids: list[int] = Field(min_length=1)
    director_ids: list[int] = Field(min_length=1)
    star_ids: list[int] = Field(min_length=1)

    @field_validator("name", "description")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be empty.")
        return value

    @field_validator("genre_ids", "director_ids", "star_ids")
    @classmethod
    def validate_unique_ids(cls, value: list[int]) -> list[int]:
        if any(item_id <= 0 for item_id in value):
            raise ValueError("Related IDs must be positive integers.")
        if len(value) != len(set(value)):
            raise ValueError("Related IDs cannot contain duplicates.")
        return value


class MovieUpdateSchema(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=250)
    year: int | None = Field(default=None, ge=1888)
    time: int | None = Field(default=None, gt=0)
    imdb: float | None = Field(default=None, ge=0, le=10)
    votes: int | None = Field(default=None, ge=0)
    meta_score: float | None = Field(default=None, ge=0, le=100)
    gross: float | None = Field(default=None, ge=0)
    description: str | None = Field(default=None, min_length=1)
    price: Decimal | None = Field(default=None, ge=0)
    certification_id: int | None = Field(default=None, gt=0)
    genre_ids: list[int] | None = Field(default=None, min_length=1)
    director_ids: list[int] | None = Field(default=None, min_length=1)
    star_ids: list[int] | None = Field(default=None, min_length=1)

    @field_validator("name", "description")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be empty.")
        return value

    @field_validator("genre_ids", "director_ids", "star_ids")
    @classmethod
    def validate_optional_unique_ids(
        cls,
        value: list[int] | None,
    ) -> list[int] | None:
        if value is None:
            return None
        if any(item_id <= 0 for item_id in value):
            raise ValueError("Related IDs must be positive integers.")
        if len(value) != len(set(value)):
            raise ValueError("Related IDs cannot contain duplicates.")
        return value

    @model_validator(mode="after")
    def reject_null_for_required_movie_fields(self) -> "MovieUpdateSchema":
        nullable_fields = {"meta_score", "gross", "price"}
        invalid_fields = sorted(
            field_name
            for field_name in self.model_fields_set
            if field_name not in nullable_fields
            and getattr(self, field_name) is None
        )
        if invalid_fields:
            raise ValueError(
                "These fields cannot be null: "
                f"{', '.join(invalid_fields)}."
            )
        return self


class MovieManagementSchema(BaseModel):
    uuid: UUID
    name: str
    year: int
    time: int
    imdb: float
    votes: int
    meta_score: float | None
    gross: float | None
    description: str
    price: Decimal | None
    certification: MovieRelatedItemSchema
    genres: list[MovieRelatedItemSchema]
    directors: list[MovieRelatedItemSchema]
    stars: list[MovieRelatedItemSchema]

    model_config = {"from_attributes": True}
