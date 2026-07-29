from uuid import uuid4

import pytest
from httpx import AsyncClient

from database.models import MovieModel

pytestmark = pytest.mark.integration


async def test_movie_catalog_uses_default_popularity_order(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
) -> None:
    response = await client.get("/api/v1/movies/")

    assert response.status_code == 200
    data = response.json()
    assert data["total_items"] == 4
    assert data["total_pages"] == 1
    assert [movie["name"] for movie in data["movies"]] == [
        "Delta Force",
        "Beta Mission",
        "Alpha Journey",
        "Gamma Story",
    ]


async def test_movie_catalog_paginates_results(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
) -> None:
    response = await client.get(
        "/api/v1/movies/",
        params={"page": 2, "per_page": 2},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert data["per_page"] == 2
    assert data["total_pages"] == 2
    assert len(data["movies"]) == 2


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"per_page": 0},
        {"per_page": 21},
        {"imdb_min": 9, "imdb_max": 5},
        {"price_min": 10, "price_max": 2},
    ],
)
async def test_movie_catalog_rejects_invalid_query_parameters(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
    params: dict[str, int],
) -> None:
    response = await client.get("/api/v1/movies/", params=params)

    assert response.status_code == 422
    assert response.json()["detail"]


async def test_movie_catalog_filters_by_year_rating_and_genre(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
) -> None:
    response = await client.get(
        "/api/v1/movies/",
        params={
            "year": 2020,
            "imdb_min": 7,
            "genre": "drama",
        },
    )

    assert response.status_code == 200
    assert [movie["name"] for movie in response.json()["movies"]] == [
        "Alpha Journey"
    ]


async def test_movie_catalog_sorts_by_price_ascending(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
) -> None:
    response = await client.get(
        "/api/v1/movies/",
        params={"sort_by": "price", "sort_order": "asc"},
    )

    assert response.status_code == 200
    prices = [float(movie["price"]) for movie in response.json()["movies"]]
    assert prices == sorted(prices)


@pytest.mark.parametrize(
    ("search", "expected_movie"),
    [
        ("Beta", "Beta Mission"),
        ("quiet family", "Gamma Story"),
        ("Alice Actor", "Delta Force"),
        ("Second Director", "Beta Mission"),
    ],
)
async def test_movie_catalog_searches_supported_fields(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
    search: str,
    expected_movie: str,
) -> None:
    response = await client.get(
        "/api/v1/movies/",
        params={"search": search},
    )

    assert response.status_code == 200
    names = [movie["name"] for movie in response.json()["movies"]]
    assert expected_movie in names


async def test_get_movie_details(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
) -> None:
    movie = seeded_movies[0]

    response = await client.get(f"/api/v1/movies/{movie.uuid}")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == movie.name
    assert data["description"] == movie.description
    assert data["certification"]["name"] == "PG-13"
    assert data["directors"][0]["name"] == "First Director"
    assert data["stars"][0]["name"] == "Alice Actor"


async def test_get_movie_details_returns_not_found(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
) -> None:
    response = await client.get(f"/api/v1/movies/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found."


async def test_genre_list_and_catalog(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
) -> None:
    genres_response = await client.get("/api/v1/genres/")

    assert genres_response.status_code == 200
    genres = genres_response.json()
    drama = next(genre for genre in genres if genre["name"] == "Drama")
    assert drama["movie_count"] == 3

    movies_response = await client.get(
        f"/api/v1/genres/{drama['id']}/movies"
    )
    assert movies_response.status_code == 200
    assert movies_response.json()["total_items"] == 3
