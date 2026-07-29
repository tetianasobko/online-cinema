import pytest
from httpx import AsyncClient

from database.models import MovieModel

pytestmark = pytest.mark.integration


async def test_favorite_movie_workflow(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
    auth_headers: dict[str, str],
) -> None:
    movie = seeded_movies[0]

    added = await client.post(
        f"/api/v1/favorites/{movie.uuid}",
        headers=auth_headers,
    )
    duplicate = await client.post(
        f"/api/v1/favorites/{movie.uuid}",
        headers=auth_headers,
    )
    favorites = await client.get(
        "/api/v1/favorites/",
        headers=auth_headers,
    )
    removed = await client.delete(
        f"/api/v1/favorites/{movie.uuid}",
        headers=auth_headers,
    )
    missing = await client.delete(
        f"/api/v1/favorites/{movie.uuid}",
        headers=auth_headers,
    )

    assert added.status_code == 201
    assert duplicate.status_code == 409
    assert favorites.status_code == 200
    assert [item["uuid"] for item in favorites.json()["movies"]] == [
        str(movie.uuid)
    ]
    assert removed.status_code == 200
    assert missing.status_code == 404


async def test_movie_reaction_workflow(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
    auth_headers: dict[str, str],
) -> None:
    movie = seeded_movies[0]
    url = f"/api/v1/movies/{movie.uuid}/reaction"

    initial = await client.get(url, headers=auth_headers)
    liked = await client.put(
        url,
        headers=auth_headers,
        json={"reaction": "like"},
    )
    changed = await client.put(
        url,
        headers=auth_headers,
        json={"reaction": "dislike"},
    )
    removed = await client.delete(url, headers=auth_headers)
    missing = await client.delete(url, headers=auth_headers)

    assert initial.status_code == 200
    assert initial.json()["reaction"] is None
    assert liked.status_code == 200
    assert liked.json()["reaction"] == "like"
    assert changed.status_code == 200
    assert changed.json()["reaction"] == "dislike"
    assert removed.status_code == 204
    assert missing.status_code == 404


async def test_movie_rating_workflow(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
    auth_headers: dict[str, str],
) -> None:
    movie = seeded_movies[0]
    url = f"/api/v1/movies/{movie.uuid}/rating"

    invalid = await client.put(
        url,
        headers=auth_headers,
        json={"rating": 11},
    )
    created = await client.put(
        url,
        headers=auth_headers,
        json={"rating": 8},
    )
    retrieved = await client.get(url, headers=auth_headers)
    updated = await client.put(
        url,
        headers=auth_headers,
        json={"rating": 10},
    )
    removed = await client.delete(url, headers=auth_headers)
    missing = await client.delete(url, headers=auth_headers)

    assert invalid.status_code == 422
    assert created.status_code == 200
    assert retrieved.json()["rating"] == 8
    assert updated.json()["rating"] == 10
    assert removed.status_code == 200
    assert removed.json()["rating"] is None
    assert missing.status_code == 404


async def test_interactions_require_authentication(
    client: AsyncClient,
    seeded_movies: list[MovieModel],
) -> None:
    movie = seeded_movies[0]

    favorite = await client.post(f"/api/v1/favorites/{movie.uuid}")
    reaction = await client.put(
        f"/api/v1/movies/{movie.uuid}/reaction",
        json={"reaction": "like"},
    )
    rating = await client.put(
        f"/api/v1/movies/{movie.uuid}/rating",
        json={"rating": 8},
    )

    assert favorite.status_code == 401
    assert reaction.status_code == 401
    assert rating.status_code == 401
