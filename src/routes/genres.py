from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import GenreModel, MovieGenresModel, MovieModel
from database.queries import get_movie_page
from database.session import get_db
from schemas.movies import (
    GenreWithMovieCountSchema,
    MovieCatalogQuerySchema,
    MovieListItemSchema,
    MovieListResponseSchema,
)


router = APIRouter()


@router.get(
    "/",
    response_model=list[GenreWithMovieCountSchema],
    status_code=status.HTTP_200_OK,
)
async def get_genres(
    db: AsyncSession = Depends(get_db),
) -> list[GenreWithMovieCountSchema]:
    statement = (
        select(
            GenreModel.id,
            GenreModel.name,
            func.count(MovieGenresModel.c.movie_id).label("movie_count"),
        )
        .outerjoin(
            MovieGenresModel,
            GenreModel.id == MovieGenresModel.c.genre_id,
        )
        .group_by(GenreModel.id, GenreModel.name)
        .order_by(GenreModel.name.asc())
    )
    rows = (await db.execute(statement)).mappings().all()
    return [GenreWithMovieCountSchema.model_validate(row) for row in rows]


@router.get(
    "/{genre_id}/movies",
    response_model=MovieListResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_genre_movies(
    genre_id: int,
    params: Annotated[MovieCatalogQuerySchema, Query()],
    db: AsyncSession = Depends(get_db),
) -> MovieListResponseSchema:
    genre_exists = await db.scalar(
        select(GenreModel.id).where(GenreModel.id == genre_id)
    )
    if genre_exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Genre not found.",
        )

    genre_condition = MovieModel.genres.any(GenreModel.id == genre_id)
    movies, total_items = await get_movie_page(
        db,
        params,
        additional_conditions=(genre_condition,),
    )
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
