from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import GenreModel
from database.session import get_db


async def get_genre_or_404(
    genre_id: int,
    db: AsyncSession = Depends(get_db),
) -> GenreModel:
    genre = await db.get(
        GenreModel,
        genre_id,
        options=(selectinload(GenreModel.movies),),
    )
    if genre is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Genre not found.",
        )
    return genre
