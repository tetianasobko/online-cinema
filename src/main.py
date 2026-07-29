from contextlib import asynccontextmanager

from fastapi import FastAPI

from database.populate import seed_user_groups
from database.session import AsyncSQLiteSessionLocal
from routes import (
    accounts_router,
    admin_carts_router,
    admin_payments_router,
    carts_router,
    comment_likes_router,
    comments_router,
    favorites_router,
    genres_router,
    movies_router,
    moderator_actors_router,
    moderator_directors_router,
    moderator_genres_router,
    moderator_movies_router,
    notifications_router,
    orders_router,
    payments_router,
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
    admin_carts_router,
    prefix=f"{api_version_prefix}/admin",
    tags=["admin cart inspection"],
)

app.include_router(
    admin_payments_router,
    prefix=f"{api_version_prefix}/admin",
    tags=["admin payment inspection"],
)

app.include_router(
    carts_router,
    prefix=f"{api_version_prefix}/cart",
    tags=["shopping cart"],
)

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
    orders_router,
    prefix=f"{api_version_prefix}/orders",
    tags=["orders"],
)

app.include_router(
    payments_router,
    prefix=f"{api_version_prefix}/payments",
    tags=["payments"],
)

app.include_router(
    notifications_router,
    prefix=f"{api_version_prefix}/notifications",
    tags=["notifications"],
)

app.include_router(
    moderator_actors_router,
    prefix=f"{api_version_prefix}/admin/actors",
    tags=["moderator actor management"],
)

app.include_router(
    moderator_directors_router,
    prefix=f"{api_version_prefix}/admin/directors",
    tags=["moderator director management"],
)

app.include_router(
    moderator_genres_router,
    prefix=f"{api_version_prefix}/admin/genres",
    tags=["moderator genre management"],
)

app.include_router(
    moderator_movies_router,
    prefix=f"{api_version_prefix}/admin/movies",
    tags=["moderator movie management"],
)
