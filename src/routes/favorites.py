from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import FavoriteMoviesModel, MovieModel, UserModel
from database.queries import favorite_exists, get_movie_page
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
    summary="Add a favorite movie",
    description="Add an existing movie to the authenticated user's favorites.",
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "The movie was not found."},
        409: {"description": "The movie is already a favorite."},
    },
)
async def add_favorite(
    movie_id: int = Depends(get_movie_id_or_404),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponseSchema:
    if await favorite_exists(db, user.id, movie_id):
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
    summary="Remove a favorite movie",
    description="Remove a movie from the authenticated user's favorites.",
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "The movie or favorite entry was not found."},
    },
)
async def remove_favorite(
    movie_id: int = Depends(get_movie_id_or_404),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponseSchema:
    if not await favorite_exists(db, user.id, movie_id):
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
    summary="Browse favorite movies",
    description=(
        "Return the authenticated user's favorites with the same search, "
        "filtering, sorting, and pagination options as the movie catalog."
    ),
    responses={401: {"description": "Authentication is required."}},
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
