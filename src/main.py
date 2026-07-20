from contextlib import asynccontextmanager

from fastapi import FastAPI

from database.populate import seed_user_groups
from database.session import AsyncSQLiteSessionLocal
from routes import accounts_router, genres_router, movies_router


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
