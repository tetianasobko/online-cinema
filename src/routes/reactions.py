from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import MovieModel, MovieReactionModel, UserModel
from database.session import get_db
from schemas.movies import (
    MovieReactionRequestSchema,
    MovieReactionResponseSchema,
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


async def _get_reaction(
    user_id: int,
    movie_id: int,
    db: AsyncSession,
) -> MovieReactionModel | None:
    return await db.scalar(
        select(MovieReactionModel).where(
            MovieReactionModel.user_id == user_id,
            MovieReactionModel.movie_id == movie_id,
        )
    )


@router.get(
    "/{movie_uuid}/reaction",
    response_model=MovieReactionResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_movie_reaction(
    movie_uuid: UUID,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MovieReactionResponseSchema:
    movie_id = await _get_movie_id(movie_uuid, db)
    reaction = await _get_reaction(user.id, movie_id, db)
    return MovieReactionResponseSchema(
        message="Movie reaction retrieved.",
        reaction=reaction.reaction if reaction is not None else None,
    )


@router.put(
    "/{movie_uuid}/reaction",
    response_model=MovieReactionResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def set_movie_reaction(
    movie_uuid: UUID,
    data: MovieReactionRequestSchema,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MovieReactionResponseSchema:
    movie_id = await _get_movie_id(movie_uuid, db)
    reaction = await _get_reaction(user.id, movie_id, db)

    if reaction is None:
        reaction = MovieReactionModel(
            user_id=user.id,
            movie_id=movie_id,
            reaction=data.reaction,
        )
        db.add(reaction)
        message = "Movie reaction added."
    elif reaction.reaction == data.reaction:
        return MovieReactionResponseSchema(
            message="Movie reaction is already set.",
            reaction=reaction.reaction,
        )
    else:
        reaction.reaction = data.reaction
        message = "Movie reaction changed."

    await db.commit()
    return MovieReactionResponseSchema(
        message=message,
        reaction=reaction.reaction,
    )


@router.delete(
    "/{movie_uuid}/reaction",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_movie_reaction(
    movie_uuid: UUID,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    movie_id = await _get_movie_id(movie_uuid, db)
    reaction = await _get_reaction(user.id, movie_id, db)

    if reaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie reaction not found.",
        )

    await db.delete(reaction)
    await db.commit()
