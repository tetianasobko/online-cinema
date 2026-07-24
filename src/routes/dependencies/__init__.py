from routes.dependencies.actors import get_actor_or_404
from routes.dependencies.directors import get_director_or_404
from routes.dependencies.genres import get_genre_or_404
from routes.dependencies.movies import get_movie_id_or_404, get_movie_or_404

__all__ = [
    "get_actor_or_404",
    "get_director_or_404",
    "get_genre_or_404",
    "get_movie_id_or_404",
    "get_movie_or_404",
]
