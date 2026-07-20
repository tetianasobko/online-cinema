from math import ceil
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from database.models import DirectorModel, GenreModel, MovieModel, StarModel
from database.session import get_db
from schemas.movies import (
    MovieDetailSchema,
    MovieListItemSchema,
    MovieListResponseSchema,
    MovieSortField,
    SortOrder,
)


router = APIRouter()


@router.get(
    "/",
    response_model=MovieListResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_movies(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=20),
    year: int | None = Query(default=None, ge=1888),
    imdb_min: float | None = Query(default=None, ge=0, le=10),
    imdb_max: float | None = Query(default=None, ge=0, le=10),
    price_min: Decimal | None = Query(default=None, ge=0),
    price_max: Decimal | None = Query(default=None, ge=0),
    genre: str | None = Query(default=None, min_length=1),
    search: str | None = Query(default=None, min_length=1),
    sort_by: MovieSortField = Query(default=MovieSortField.POPULARITY),
    sort_order: SortOrder = Query(default=SortOrder.DESC),
    db: AsyncSession = Depends(get_db),
) -> MovieListResponseSchema:
    if imdb_min is not None and imdb_max is not None and imdb_min > imdb_max:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="imdb_min cannot be greater than imdb_max.",
        )
    if (
        price_min is not None
        and price_max is not None
        and price_min > price_max
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="price_min cannot be greater than price_max.",
        )

    conditions: list[ColumnElement[bool]] = []
    if year is not None:
        conditions.append(MovieModel.year == year)
    if imdb_min is not None:
        conditions.append(MovieModel.imdb >= imdb_min)
    if imdb_max is not None:
        conditions.append(MovieModel.imdb <= imdb_max)
    if price_min is not None:
        conditions.append(MovieModel.price >= price_min)
    if price_max is not None:
        conditions.append(MovieModel.price <= price_max)
    if genre is not None:
        conditions.append(
            MovieModel.genres.any(
                func.lower(GenreModel.name) == genre.strip().lower()
            )
        )
    if search is not None and (search_term := search.strip()):
        pattern = f"%{search_term}%"
        conditions.append(
            or_(
                MovieModel.name.ilike(pattern),
                MovieModel.description.ilike(pattern),
                MovieModel.stars.any(StarModel.name.ilike(pattern)),
                MovieModel.directors.any(DirectorModel.name.ilike(pattern)),
            )
        )

    count_statement = select(func.count(MovieModel.id)).where(*conditions)
    total_items = await db.scalar(count_statement) or 0

    sort_columns = {
        MovieSortField.PRICE: MovieModel.price,
        MovieSortField.YEAR: MovieModel.year,
        MovieSortField.IMDB: MovieModel.imdb,
        MovieSortField.POPULARITY: MovieModel.votes,
    }
    sort_column = sort_columns[sort_by]
    order_by = (
        sort_column.asc()
        if sort_order == SortOrder.ASC
        else sort_column.desc()
    )

    statement = (
        select(MovieModel)
        .options(selectinload(MovieModel.genres))
        .where(*conditions)
        .order_by(order_by, MovieModel.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    movies = list((await db.scalars(statement)).all())
    movie_items = [
        MovieListItemSchema.model_validate(movie) for movie in movies
    ]

    return MovieListResponseSchema(
        movies=movie_items,
        page=page,
        per_page=per_page,
        total_pages=ceil(total_items / per_page) if total_items else 0,
        total_items=total_items,
    )


@router.get(
    "/{movie_uuid}",
    response_model=MovieDetailSchema,
    status_code=status.HTTP_200_OK,
)
async def get_movie_detail(
    movie_uuid: UUID,
    db: AsyncSession = Depends(get_db),
) -> MovieDetailSchema:
    statement = (
        select(MovieModel)
        .options(
            joinedload(MovieModel.certification),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.directors),
            selectinload(MovieModel.stars),
        )
        .where(MovieModel.uuid == movie_uuid)
    )
    movie = await db.scalar(statement)

    if movie is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found.",
        )

    return MovieDetailSchema.model_validate(movie)
