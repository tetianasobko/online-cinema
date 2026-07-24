from contextlib import asynccontextmanager

from fastapi import FastAPI

from database.populate import seed_user_groups
from database.session import AsyncSQLiteSessionLocal
from routes import (
    accounts_router,
    comment_likes_router,
    comments_router,
    favorites_router,
    genres_router,
    movies_router,
    moderator_movies_router,
    notifications_router,
    ratings_router,
    reactions_router,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with AsyncSQLiteSessionLocal() as session:
        await seed_user_groups(session)
    yield


app = FastAPI(
    title="Online Cinema",
    lifespan=lifespan,
)

api_version_prefix = "/api/v1"

app.include_router(
    accounts_router,
    prefix=f"{api_version_prefix}/accounts",
    tags=["accounts"]
)

app.include_router(
    movies_router,
    prefix=f"{api_version_prefix}/movies",
    tags=["movies"],
)

app.include_router(
    genres_router,
    prefix=f"{api_version_prefix}/genres",
    tags=["genres"],
)

app.include_router(
    favorites_router,
    prefix=f"{api_version_prefix}/favorites",
    tags=["favorites"],
)

app.include_router(
    reactions_router,
    prefix=f"{api_version_prefix}/movies",
    tags=["movie reactions"],
)

app.include_router(
    ratings_router,
    prefix=f"{api_version_prefix}/movies",
    tags=["movie ratings"],
)

app.include_router(
    comments_router,
    prefix=api_version_prefix,
    tags=["movie comments"],
)

app.include_router(
    comment_likes_router,
    prefix=api_version_prefix,
    tags=["comment likes"],
)

app.include_router(
    notifications_router,
    prefix=f"{api_version_prefix}/notifications",
    tags=["notifications"],
)

app.include_router(
    moderator_movies_router,
    prefix=f"{api_version_prefix}/admin/movies",
    tags=["moderator movie management"],
)
