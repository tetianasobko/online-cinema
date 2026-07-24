from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from database.models import MovieModel
from database.queries import get_movie_id_by_uuid
from database.session import get_db


async def get_movie_or_404(
    movie_uuid: UUID,
    db: AsyncSession = Depends(get_db),
) -> MovieModel:
    movie = await db.scalar(
        select(MovieModel)
        .options(
            joinedload(MovieModel.certification),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.directors),
            selectinload(MovieModel.stars),
        )
        .where(MovieModel.uuid == movie_uuid)
    )
    if movie is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found.",
        )
    return movie


async def get_movie_id_or_404(
    movie_uuid: UUID,
    db: AsyncSession = Depends(get_db),
) -> int:
    movie_id = await get_movie_id_by_uuid(db, movie_uuid)
    if movie_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found.",
        )
    return movie_id
