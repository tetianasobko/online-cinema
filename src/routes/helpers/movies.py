from collections.abc import Sequence
from math import ceil

from database.models import MovieModel
from schemas.movies import (
    MovieCatalogQuerySchema,
    MovieListItemSchema,
    MovieListResponseSchema,
)


def build_movie_list_response(
    movies: Sequence[MovieModel],
    total_items: int,
    params: MovieCatalogQuerySchema,
) -> MovieListResponseSchema:
    return MovieListResponseSchema(
        movies=[
            MovieListItemSchema.model_validate(movie) for movie in movies
        ],
        page=params.page,
        per_page=params.per_page,
        total_pages=(
            ceil(total_items / params.per_page) if total_items else 0
        ),
        total_items=total_items,
    )
