from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import FavoriteMoviesModel, MovieModel, UserModel
from database.queries import get_movie_page
from database.session import get_db
from routes.dependencies import get_movie_id_or_404
from routes.helpers import build_movie_list_response
from schemas.accounts import MessageResponseSchema
from schemas.movies import (
    MovieCatalogQuerySchema,
    MovieListResponseSchema,
)
from security.authorization import get_current_user


router = APIRouter()


@router.post(
    "/{movie_uuid}",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def add_favorite(
    movie_id: int = Depends(get_movie_id_or_404),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponseSchema:
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
    movie_id: int = Depends(get_movie_id_or_404),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponseSchema:
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
    return build_movie_list_response(movies, total_items, params)
