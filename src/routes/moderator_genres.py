from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import GenreModel
from database.session import get_db
from routes.dependencies import get_genre_or_404
from schemas.moderator import (
    GenreCreateSchema,
    GenreManagementSchema,
    GenreUpdateSchema,
)
from security.authorization import require_moderator


router = APIRouter(dependencies=[Depends(require_moderator)])


def _duplicate_genre_error(error: IntegrityError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="A genre with this name already exists.",
    )


@router.post(
    "/",
    response_model=GenreManagementSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_genre(
    data: GenreCreateSchema,
    db: AsyncSession = Depends(get_db),
) -> GenreManagementSchema:
    genre = GenreModel(name=data.name)
    db.add(genre)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise _duplicate_genre_error(error) from error
    return GenreManagementSchema.model_validate(genre)


@router.get(
    "/{genre_id}",
    response_model=GenreManagementSchema,
    status_code=status.HTTP_200_OK,
)
async def get_genre(
    genre: GenreModel = Depends(get_genre_or_404),
) -> GenreManagementSchema:
    return GenreManagementSchema.model_validate(genre)


@router.patch(
    "/{genre_id}",
    response_model=GenreManagementSchema,
    status_code=status.HTTP_200_OK,
)
async def update_genre(
    data: GenreUpdateSchema,
    genre: GenreModel = Depends(get_genre_or_404),
    db: AsyncSession = Depends(get_db),
) -> GenreManagementSchema:
    genre.name = data.name
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise _duplicate_genre_error(error) from error
    return GenreManagementSchema.model_validate(genre)


@router.delete(
    "/{genre_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_genre(
    genre: GenreModel = Depends(get_genre_or_404),
    db: AsyncSession = Depends(get_db),
) -> Response:
    genre.movies.clear()
    await db.delete(genre)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
