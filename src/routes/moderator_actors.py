from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import StarModel
from database.session import get_db
from routes.dependencies import get_actor_or_404
from schemas.moderator import (
    ActorCreateSchema,
    ActorManagementSchema,
    ActorUpdateSchema,
)
from security.authorization import require_moderator


router = APIRouter(dependencies=[Depends(require_moderator)])


def _duplicate_actor_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="An actor with this name already exists.",
    )


@router.post(
    "/",
    response_model=ActorManagementSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_actor(
    data: ActorCreateSchema,
    db: AsyncSession = Depends(get_db),
) -> ActorManagementSchema:
    actor = StarModel(name=data.name)
    db.add(actor)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise _duplicate_actor_error() from error
    return ActorManagementSchema.model_validate(actor)


@router.get(
    "/{actor_id}",
    response_model=ActorManagementSchema,
    status_code=status.HTTP_200_OK,
)
async def get_actor(
    actor: StarModel = Depends(get_actor_or_404),
) -> ActorManagementSchema:
    return ActorManagementSchema.model_validate(actor)


@router.patch(
    "/{actor_id}",
    response_model=ActorManagementSchema,
    status_code=status.HTTP_200_OK,
)
async def update_actor(
    data: ActorUpdateSchema,
    actor: StarModel = Depends(get_actor_or_404),
    db: AsyncSession = Depends(get_db),
) -> ActorManagementSchema:
    actor.name = data.name
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise _duplicate_actor_error() from error
    return ActorManagementSchema.model_validate(actor)


@router.delete(
    "/{actor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_actor(
    actor: StarModel = Depends(get_actor_or_404),
    db: AsyncSession = Depends(get_db),
) -> Response:
    actor.movies.clear()
    await db.delete(actor)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
