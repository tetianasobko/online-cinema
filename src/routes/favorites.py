from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import FavoriteMoviesModel, MovieModel, UserModel
from database.queries import get_movie_page
from database.session import get_db
from schemas.accounts import MessageResponseSchema
from schemas.movies import (
    MovieCatalogQuerySchema,
    MovieListItemSchema,
    MovieListResponseSchema,
)
from security.authorization import get_current_user


router = APIRouter()


async def _get_movie_id(movie_uuid: UUID, db: AsyncSession) -> int:
    movie_id = await db.scalar(
        select(MovieModel.id).where(MovieModel.uuid == movie_uuid)
    )
    if movie_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found.",
        )
    return movie_id


@router.post(
    "/{movie_uuid}",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def add_favorite(
    movie_uuid: UUID,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponseSchema:
    movie_id = await _get_movie_id(movie_uuid, db)
    favorite_exists = await db.scalar(
        select(FavoriteMoviesModel.c.movie_id).where(
            FavoriteMoviesModel.c.user_id == user.id,
            FavoriteMoviesModel.c.movie_id == movie_id,
        )
    )
    if favorite_exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Movie is already in favorites.",
        )

    await db.execute(
        insert(FavoriteMoviesModel).values(
            user_id=user.id,
            movie_id=movie_id,
        )
    )
    await db.commit()
    return MessageResponseSchema(message="Movie added to favorites.")


@router.delete(
    "/{movie_uuid}",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def remove_favorite(
    movie_uuid: UUID,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponseSchema:
    movie_id = await _get_movie_id(movie_uuid, db)
    favorite_exists = await db.scalar(
        select(FavoriteMoviesModel.c.movie_id).where(
            FavoriteMoviesModel.c.user_id == user.id,
            FavoriteMoviesModel.c.movie_id == movie_id,
        )
    )
    if favorite_exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie is not in favorites.",
        )

    await db.execute(
        delete(FavoriteMoviesModel).where(
            FavoriteMoviesModel.c.user_id == user.id,
            FavoriteMoviesModel.c.movie_id == movie_id,
        )
    )
    await db.commit()
    return MessageResponseSchema(message="Movie removed from favorites.")


@router.get(
    "/",
    response_model=MovieListResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_favorites(
    params: Annotated[MovieCatalogQuerySchema, Query()],
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MovieListResponseSchema:
    favorite_condition = MovieModel.id.in_(
        select(FavoriteMoviesModel.c.movie_id).where(
            FavoriteMoviesModel.c.user_id == user.id
        )
    )
    movies, total_items = await get_movie_page(
        db,
        params,
        additional_conditions=(favorite_condition,),
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
