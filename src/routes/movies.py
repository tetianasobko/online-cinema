from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from database.models import MovieModel
from database.session import get_db
from schemas.movies import (
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
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
) -> MovieListResponseSchema:
    total_items = await db.scalar(select(func.count(MovieModel.id))) or 0

    statement = (
        select(MovieModel)
        .options(selectinload(MovieModel.genres))
        .order_by(MovieModel.id.desc())
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
