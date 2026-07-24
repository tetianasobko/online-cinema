from routes.accounts import router as accounts_router
from routes.admin_carts import router as admin_carts_router
from routes.carts import router as carts_router
from routes.comment_likes import router as comment_likes_router
from routes.comments import router as comments_router
from routes.favorites import router as favorites_router
from routes.genres import router as genres_router
from routes.movies import router as movies_router
from routes.moderator_actors import router as moderator_actors_router
from routes.moderator_directors import router as moderator_directors_router
from routes.moderator_genres import router as moderator_genres_router
from routes.moderator_movies import router as moderator_movies_router
from routes.notifications import router as notifications_router
from routes.orders import router as orders_router
from routes.reactions import router as reactions_router
from routes.ratings import router as ratings_router

__all__ = [
    "accounts_router",
    "admin_carts_router",
    "carts_router",
    "comment_likes_router",
    "comments_router",
    "favorites_router",
    "genres_router",
    "movies_router",
    "moderator_actors_router",
    "moderator_directors_router",
    "moderator_genres_router",
    "moderator_movies_router",
    "notifications_router",
    "orders_router",
    "reactions_router",
    "ratings_router",
]
