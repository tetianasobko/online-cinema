from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.queries import get_movie_id_by_uuid
from database.session import get_db


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
