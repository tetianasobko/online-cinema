from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from database.models import MovieModel
from database.queries import get_movie_page
from database.session import get_db
from schemas.movies import (
    MovieCatalogQuerySchema,
    MovieDetailSchema,
    MovieListItemSchema,
    MovieListResponseSchema,
)


router = APIRouter()


@router.get(
    "/",
    response_model=MovieListResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_movies(
    params: Annotated[MovieCatalogQuerySchema, Query()],
    db: AsyncSession = Depends(get_db),
) -> MovieListResponseSchema:
    movies, total_items = await get_movie_page(db, params)
    movie_items = [
        MovieListItemSchema.model_validate(movie) for movie in movies
    ]

    return MovieListResponseSchema(
        movies=movie_items,
        page=params.page,
        per_page=params.per_page,
        total_pages=(
            ceil(total_items / params.per_page) if total_items else 0
        ),
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
