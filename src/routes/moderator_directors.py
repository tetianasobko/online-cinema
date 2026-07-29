from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import DirectorModel
from database.session import get_db
from routes.dependencies import get_director_or_404
from schemas.moderator import (
    DirectorCreateSchema,
    DirectorManagementSchema,
    DirectorUpdateSchema,
)
from security.authorization import require_moderator


router = APIRouter(dependencies=[Depends(require_moderator)])


def _duplicate_director_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="A director with this name already exists.",
    )


@router.post(
    "/",
    response_model=DirectorManagementSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a director",
    description="Allow a moderator to create a uniquely named director.",
    responses={
        401: {"description": "Authentication is required."},
        403: {"description": "Moderator access is required."},
        409: {"description": "A director with this name already exists."},
    },
)
async def create_director(
    data: DirectorCreateSchema,
    db: AsyncSession = Depends(get_db),
) -> DirectorManagementSchema:
    director = DirectorModel(name=data.name)
    db.add(director)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise _duplicate_director_error() from error
    return DirectorManagementSchema.model_validate(director)


@router.get(
    "/{director_id}",
    response_model=DirectorManagementSchema,
    status_code=status.HTTP_200_OK,
    summary="Get a director for management",
    description="Return one director for the moderator interface.",
    responses={
        401: {"description": "Authentication is required."},
        403: {"description": "Moderator access is required."},
        404: {"description": "The director was not found."},
    },
)
async def get_director(
    director: DirectorModel = Depends(get_director_or_404),
) -> DirectorManagementSchema:
    return DirectorManagementSchema.model_validate(director)


@router.patch(
    "/{director_id}",
    response_model=DirectorManagementSchema,
    status_code=status.HTTP_200_OK,
    summary="Update a director",
    description="Allow a moderator to rename an existing director.",
    responses={
        401: {"description": "Authentication is required."},
        403: {"description": "Moderator access is required."},
        404: {"description": "The director was not found."},
        409: {"description": "A director with this name already exists."},
    },
)
async def update_director(
    data: DirectorUpdateSchema,
    director: DirectorModel = Depends(get_director_or_404),
    db: AsyncSession = Depends(get_db),
) -> DirectorManagementSchema:
    director.name = data.name
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise _duplicate_director_error() from error
    return DirectorManagementSchema.model_validate(director)


@router.delete(
    "/{director_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a director",
    description="Allow a moderator to delete a director and their movie links.",
    responses={
        401: {"description": "Authentication is required."},
        403: {"description": "Moderator access is required."},
        404: {"description": "The director was not found."},
    },
)
async def delete_director(
    director: DirectorModel = Depends(get_director_or_404),
    db: AsyncSession = Depends(get_db),
) -> Response:
    director.movies.clear()
    await db.delete(director)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
