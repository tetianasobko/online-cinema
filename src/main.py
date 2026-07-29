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
    docs_router,
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

OPENAPI_TAGS = [
    {"name": "accounts", "description": "Registration, authentication, and account management."},
    {"name": "movies", "description": "Public movie catalog and movie details."},
    {"name": "genres", "description": "Genre discovery and genre movie catalogs."},
    {"name": "favorites", "description": "Authenticated users' favorite movies."},
    {"name": "movie reactions", "description": "Movie likes and dislikes."},
    {"name": "movie ratings", "description": "Movie ratings on a 10-point scale."},
    {"name": "movie comments", "description": "Movie comments and replies."},
    {"name": "comment likes", "description": "Likes on comments and replies."},
    {"name": "shopping cart", "description": "Authenticated users' shopping carts."},
    {"name": "orders", "description": "Order creation, history, and cancellation."},
    {"name": "payments", "description": "Stripe Checkout, webhooks, history, and refunds."},
    {"name": "notifications", "description": "Comment reply and like notifications."},
    {"name": "admin cart inspection", "description": "Administrator cart inspection."},
    {"name": "admin payment inspection", "description": "Administrator payment reporting."},
    {"name": "moderator actor management", "description": "Moderator CRUD operations for actors."},
    {"name": "moderator director management", "description": "Moderator CRUD operations for directors."},
    {"name": "moderator genre management", "description": "Moderator CRUD operations for genres."},
    {"name": "moderator movie management", "description": "Moderator CRUD operations for movies."},
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with AsyncSQLiteSessionLocal() as session:
        await seed_user_groups(session)
    yield


app = FastAPI(
    title="Online Cinema",
    description=(
        "API for browsing and purchasing movies, managing user interactions, "
        "and administering the online cinema catalog."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    openapi_tags=OPENAPI_TAGS,
)

api_version_prefix = "/api/v1"

app.include_router(docs_router)


@app.get("/health", include_in_schema=False)
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


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
