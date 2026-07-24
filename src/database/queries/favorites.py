from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import FavoriteMoviesModel


async def favorite_exists(
    db: AsyncSession,
    user_id: int,
    movie_id: int,
) -> bool:
    favorite_movie_id = await db.scalar(
        select(FavoriteMoviesModel.c.movie_id).where(
            FavoriteMoviesModel.c.user_id == user_id,
            FavoriteMoviesModel.c.movie_id == movie_id,
        )
    )
    return favorite_movie_id is not None
