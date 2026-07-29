
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import MovieRatingModel, UserModel
from database.session import get_db
from routes.dependencies import get_movie_id_or_404
from schemas.movies import MovieRatingRequestSchema, MovieRatingResponseSchema
from security.authorization import get_current_user


router = APIRouter()


async def _get_rating(
    user_id: int,
    movie_id: int,
    db: AsyncSession,
) -> MovieRatingModel | None:
    return await db.scalar(
        select(MovieRatingModel).where(
            MovieRatingModel.user_id == user_id,
            MovieRatingModel.movie_id == movie_id,
        )
    )


@router.get(
    "/{movie_uuid}/rating",
    response_model=MovieRatingResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get a movie rating",
    description="Return the authenticated user's rating for a movie.",
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "The movie was not found."},
    },
)
async def get_movie_rating(
    movie_id: int = Depends(get_movie_id_or_404),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MovieRatingResponseSchema:
    rating = await _get_rating(user.id, movie_id, db)
    return MovieRatingResponseSchema(
        message="Movie rating retrieved.",
        rating=rating.rating if rating is not None else None,
    )


@router.put(
    "/{movie_uuid}/rating",
    response_model=MovieRatingResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Set a movie rating",
    description="Add or update a movie rating on the 10-point scale.",
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "The movie was not found."},
        422: {"description": "The rating is outside the allowed range."},
    },
)
async def set_movie_rating(
    data: MovieRatingRequestSchema,
    movie_id: int = Depends(get_movie_id_or_404),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MovieRatingResponseSchema:
    rating = await _get_rating(user.id, movie_id, db)

    if rating is None:
        rating = MovieRatingModel(
            user_id=user.id,
            movie_id=movie_id,
            rating=data.rating,
        )
        db.add(rating)
        message = "Movie rating added."
    elif rating.rating == data.rating:
        return MovieRatingResponseSchema(
            message="Movie rating is already set.",
            rating=rating.rating,
        )
    else:
        rating.rating = data.rating
        message = "Movie rating changed."

    await db.commit()
    return MovieRatingResponseSchema(message=message, rating=rating.rating)


@router.delete(
    "/{movie_uuid}/rating",
    response_model=MovieRatingResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Remove a movie rating",
    description="Delete the authenticated user's rating for a movie.",
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "The movie or rating was not found."},
    },
)
async def remove_movie_rating(
    movie_id: int = Depends(get_movie_id_or_404),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MovieRatingResponseSchema:
    rating = await _get_rating(user.id, movie_id, db)

    if rating is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie rating not found.",
        )

    await db.delete(rating)
    await db.commit()
    return MovieRatingResponseSchema(
        message="Movie rating removed.",
        rating=None,
    )
