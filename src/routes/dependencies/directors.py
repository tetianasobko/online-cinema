from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import DirectorModel
from database.session import get_db


async def get_director_or_404(
    director_id: int,
    db: AsyncSession = Depends(get_db),
) -> DirectorModel:
    director = await db.get(
        DirectorModel,
        director_id,
        options=(selectinload(DirectorModel.movies),),
    )
    if director is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Director not found.",
        )
    return director
