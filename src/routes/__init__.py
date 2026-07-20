from routes.accounts import router as accounts_router
from routes.favorites import router as favorites_router
from routes.genres import router as genres_router
from routes.movies import router as movies_router

__all__ = [
    "accounts_router",
    "favorites_router",
    "genres_router",
    "movies_router",
]
