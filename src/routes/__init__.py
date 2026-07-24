from routes.accounts import router as accounts_router
from routes.comment_likes import router as comment_likes_router
from routes.comments import router as comments_router
from routes.favorites import router as favorites_router
from routes.genres import router as genres_router
from routes.movies import router as movies_router
from routes.reactions import router as reactions_router
from routes.ratings import router as ratings_router

__all__ = [
    "accounts_router",
    "comment_likes_router",
    "comments_router",
    "favorites_router",
    "genres_router",
    "movies_router",
    "reactions_router",
    "ratings_router",
]
