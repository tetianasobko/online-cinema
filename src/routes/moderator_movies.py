from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    CartItemModel,
    CertificationModel,
    DirectorModel,
    GenreModel,
    MovieModel,
    OrderItemModel,
    OrderModel,
    OrderStatusEnum,
    StarModel,
)
from database.session import get_db
from routes.dependencies import get_movie_or_404
from schemas.accounts import MessageResponseSchema
from schemas.moderator import (
    MovieCreateSchema,
    MovieManagementSchema,
    MovieUpdateSchema,
)
from security.authorization import require_moderator


router = APIRouter(dependencies=[Depends(require_moderator)])


async def _get_related_entities(
    db: AsyncSession,
    model: Any,
    entity_ids: list[int],
    entity_name: str,
) -> list[Any]:
    entities = list(
        (
            await db.scalars(
                select(model).where(model.id.in_(entity_ids))
            )
        ).all()
    )
    found_ids = {entity.id for entity in entities}
    missing_ids = sorted(set(entity_ids) - found_ids)
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown {entity_name} IDs: {missing_ids}.",
        )
    return entities


async def _get_certification(
    db: AsyncSession,
    certification_id: int,
) -> CertificationModel:
    certification = await db.get(CertificationModel, certification_id)
    if certification is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown certification ID: {certification_id}.",
        )
    return certification


@router.post(
    "/",
    response_model=MovieManagementSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a movie",
    description=(
        "Allow a moderator to create a movie and assign its certification, "
        "genres, directors, and actors."
    ),
    responses={
        401: {"description": "Authentication is required."},
        403: {"description": "Moderator access is required."},
        409: {"description": "The movie uniqueness constraint was violated."},
        422: {"description": "A related entity ID is invalid."},
    },
)
async def create_movie(
    data: MovieCreateSchema,
    db: AsyncSession = Depends(get_db),
) -> MovieManagementSchema:
    certification = await _get_certification(db, data.certification_id)
    genres = await _get_related_entities(
        db, GenreModel, data.genre_ids, "genre"
    )
    directors = await _get_related_entities(
        db, DirectorModel, data.director_ids, "director"
    )
    stars = await _get_related_entities(
        db, StarModel, data.star_ids, "star"
    )
    movie = MovieModel(
        **data.model_dump(
            exclude={
                "certification_id",
                "genre_ids",
                "director_ids",
                "star_ids",
            }
        ),
        certification=certification,
        genres=genres,
        directors=directors,
        stars=stars,
    )
    db.add(movie)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A movie with the same name, year, and time already exists.",
        ) from error
    return MovieManagementSchema.model_validate(movie)


@router.get(
    "/{movie_uuid}",
    response_model=MovieManagementSchema,
    status_code=status.HTTP_200_OK,
    summary="Get a movie for management",
    description="Return complete movie data for the moderator interface.",
    responses={
        401: {"description": "Authentication is required."},
        403: {"description": "Moderator access is required."},
        404: {"description": "The movie was not found."},
    },
)
async def get_movie(
    movie_uuid: UUID,
    db: AsyncSession = Depends(get_db),
) -> MovieManagementSchema:
    movie = await get_movie_or_404(movie_uuid, db)
    return MovieManagementSchema.model_validate(movie)


@router.patch(
    "/{movie_uuid}",
    response_model=MovieManagementSchema,
    status_code=status.HTTP_200_OK,
    summary="Update a movie",
    description="Allow a moderator to update movie fields and relationships.",
    responses={
        401: {"description": "Authentication is required."},
        403: {"description": "Moderator access is required."},
        404: {"description": "The movie was not found."},
        409: {"description": "The movie uniqueness constraint was violated."},
        422: {"description": "A related entity ID is invalid."},
    },
)
async def update_movie(
    movie_uuid: UUID,
    data: MovieUpdateSchema,
    db: AsyncSession = Depends(get_db),
) -> MovieManagementSchema:
    movie = await get_movie_or_404(movie_uuid, db)
    changes = data.model_dump(exclude_unset=True)

    if "certification_id" in changes:
        movie.certification = await _get_certification(
            db, changes.pop("certification_id")
        )
    if "genre_ids" in changes:
        movie.genres = await _get_related_entities(
            db, GenreModel, changes.pop("genre_ids"), "genre"
        )
    if "director_ids" in changes:
        movie.directors = await _get_related_entities(
            db, DirectorModel, changes.pop("director_ids"), "director"
        )
    if "star_ids" in changes:
        movie.stars = await _get_related_entities(
            db, StarModel, changes.pop("star_ids"), "star"
        )
    for field_name, value in changes.items():
        setattr(movie, field_name, value)

    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A movie with the same name, year, and time already exists.",
        ) from error
    return MovieManagementSchema.model_validate(movie)


@router.delete(
    "/{movie_uuid}",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Delete a movie",
    description=(
        "Delete a movie only when it has not been purchased, is not present "
        "in a user's cart, and has no blocking references."
    ),
    responses={
        401: {"description": "Authentication is required."},
        403: {"description": "Moderator access is required."},
        404: {"description": "The movie was not found."},
        409: {
            "description": (
                "The movie was purchased, is in a cart, or is still referenced."
            )
        },
    },
)
async def delete_movie(
    movie_uuid: UUID,
    db: AsyncSession = Depends(get_db),
) -> MessageResponseSchema:
    movie = await get_movie_or_404(movie_uuid, db)

    purchase_exists = await db.scalar(
        select(OrderItemModel.id)
        .join(OrderModel)
        .where(
            OrderItemModel.movie_id == movie.id,
            OrderModel.status == OrderStatusEnum.PAID,
        )
        .limit(1)
    )
    if purchase_exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This movie cannot be deleted because it has been purchased."
            ),
        )

    affected_carts = await db.scalar(
        select(func.count(func.distinct(CartItemModel.cart_id))).where(
            CartItemModel.movie_id == movie.id
        )
    ) or 0
    if affected_carts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This movie cannot be deleted because it is currently in "
                f"{affected_carts} user cart(s)."
            ),
        )

    await db.delete(movie)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This movie cannot be deleted because it is referenced "
                "by existing records."
            ),
        ) from error

    return MessageResponseSchema(message="Movie deleted successfully.")
