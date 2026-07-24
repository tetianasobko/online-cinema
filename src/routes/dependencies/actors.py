from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import StarModel
from database.session import get_db


async def get_actor_or_404(
    actor_id: int,
    db: AsyncSession = Depends(get_db),
) -> StarModel:
    actor = await db.get(
        StarModel,
        actor_id,
        options=(selectinload(StarModel.movies),),
    )
    if actor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actor not found.",
        )
    return actor
