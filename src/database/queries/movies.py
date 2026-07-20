from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import DirectorModel, GenreModel, MovieModel, StarModel
from schemas.movies import (
    MovieCatalogQuerySchema,
    MovieSortField,
    SortOrder,
)


def _build_conditions(
    params: MovieCatalogQuerySchema,
) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []

    if params.year is not None:
        conditions.append(MovieModel.year == params.year)
    if params.imdb_min is not None:
        conditions.append(MovieModel.imdb >= params.imdb_min)
    if params.imdb_max is not None:
        conditions.append(MovieModel.imdb <= params.imdb_max)
    if params.price_min is not None:
        conditions.append(MovieModel.price >= params.price_min)
    if params.price_max is not None:
        conditions.append(MovieModel.price <= params.price_max)
    if params.genre is not None:
        conditions.append(
            MovieModel.genres.any(
                func.lower(GenreModel.name) == params.genre.strip().lower()
            )
        )
    if params.search is not None and (search_term := params.search.strip()):
        pattern = f"%{search_term}%"
        conditions.append(
            or_(
                MovieModel.name.ilike(pattern),
                MovieModel.description.ilike(pattern),
                MovieModel.stars.any(StarModel.name.ilike(pattern)),
                MovieModel.directors.any(DirectorModel.name.ilike(pattern)),
            )
        )

    return conditions


def _get_ordering(params: MovieCatalogQuerySchema) -> tuple[Any, Any]:
    sort_columns = {
        MovieSortField.PRICE: MovieModel.price,
        MovieSortField.YEAR: MovieModel.year,
        MovieSortField.IMDB: MovieModel.imdb,
        MovieSortField.POPULARITY: MovieModel.votes,
    }
    sort_column = sort_columns[params.sort_by]
    ordering = (
        sort_column.asc()
        if params.sort_order == SortOrder.ASC
        else sort_column.desc()
    )
    return ordering, MovieModel.id.desc()


async def get_movie_page(
    db: AsyncSession,
    params: MovieCatalogQuerySchema,
    additional_conditions: Sequence[ColumnElement[bool]] = (),
) -> tuple[list[MovieModel], int]:
    conditions = [*_build_conditions(params), *additional_conditions]

    count_statement = select(func.count(MovieModel.id)).where(*conditions)
    total_items = await db.scalar(count_statement) or 0

    statement = (
        select(MovieModel)
        .options(selectinload(MovieModel.genres))
        .where(*conditions)
        .order_by(*_get_ordering(params))
        .offset((params.page - 1) * params.per_page)
        .limit(params.per_page)
    )
    movies = list((await db.scalars(statement)).all())
    return movies, total_items
