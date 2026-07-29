from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from database.models import (
    MovieModel,
    MovieRatingModel,
    MovieReactionEnum,
    MovieReactionModel,
)
from database.queries import get_movie_page
from database.session import get_db
from routes.helpers import build_movie_list_response
from schemas.movies import (
    MovieCatalogQuerySchema,
    MovieDetailSchema,
    MovieListResponseSchema,
)


router = APIRouter()


@router.get(
    "/",
    response_model=MovieListResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Browse the movie catalog",
    description=(
        "Return a paginated movie catalog with supported search, filtering, "
        "and sorting options."
    ),
)
async def get_movies(
    params: Annotated[MovieCatalogQuerySchema, Query()],
    db: AsyncSession = Depends(get_db),
) -> MovieListResponseSchema:
    movies, total_items = await get_movie_page(db, params)
    return build_movie_list_response(movies, total_items, params)


@router.get(
    "/{movie_uuid}",
    response_model=MovieDetailSchema,
    status_code=status.HTTP_200_OK,
    summary="Get movie details",
    description=(
        "Return the complete movie description, related entities, reaction "
        "counts, and rating statistics."
    ),
    responses={404: {"description": "The movie was not found."}},
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

    reaction_counts = await db.execute(
        select(
            func.count().filter(
                MovieReactionModel.reaction == MovieReactionEnum.LIKE
            ),
            func.count().filter(
                MovieReactionModel.reaction == MovieReactionEnum.DISLIKE
            ),
        ).where(MovieReactionModel.movie_id == movie.id)
    )
    likes_count, dislikes_count = reaction_counts.one()
    rating_stats = await db.execute(
        select(
            func.avg(MovieRatingModel.rating),
            func.count(MovieRatingModel.rating),
        ).where(MovieRatingModel.movie_id == movie.id)
    )
    average_rating, ratings_count = rating_stats.one()
    detail = MovieDetailSchema.model_validate(movie)
    return detail.model_copy(
        update={
            "likes_count": likes_count,
            "dislikes_count": dislikes_count,
            "average_rating": (
                round(float(average_rating), 2)
                if average_rating is not None
                else None
            ),
            "ratings_count": ratings_count,
        }
    )
