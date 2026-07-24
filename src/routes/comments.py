from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import MovieCommentModel, UserModel
from database.session import get_db
from routes.dependencies import get_movie_id_or_404
from schemas.movies import (
    MovieCommentCreateSchema,
    MovieCommentListSchema,
    MovieCommentReplySchema,
    MovieCommentSchema,
)
from security.authorization import get_current_user


router = APIRouter()


@router.get(
    "/movies/{movie_uuid}/comments",
    response_model=MovieCommentListSchema,
    status_code=status.HTTP_200_OK,
)
async def get_movie_comments(
    movie_id: int = Depends(get_movie_id_or_404),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> MovieCommentListSchema:
    root_conditions = (
        MovieCommentModel.movie_id == movie_id,
        MovieCommentModel.parent_id.is_(None),
    )
    total_items = await db.scalar(
        select(func.count(MovieCommentModel.id)).where(*root_conditions)
    ) or 0
    statement = (
        select(MovieCommentModel)
        .options(selectinload(MovieCommentModel.replies))
        .where(*root_conditions)
        .order_by(MovieCommentModel.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    comments = list((await db.scalars(statement)).all())

    return MovieCommentListSchema(
        comments=[
            MovieCommentSchema.model_validate(comment)
            for comment in comments
        ],
        page=page,
        per_page=per_page,
        total_pages=ceil(total_items / per_page) if total_items else 0,
        total_items=total_items,
    )


@router.post(
    "/movies/{movie_uuid}/comments",
    response_model=MovieCommentSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_movie_comment(
    data: MovieCommentCreateSchema,
    movie_id: int = Depends(get_movie_id_or_404),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MovieCommentSchema:
    comment = MovieCommentModel(
        text=data.text,
        user_id=user.id,
        movie_id=movie_id,
        replies=[],
    )
    db.add(comment)
    await db.commit()
    saved_comment = (
        await db.scalars(
            select(MovieCommentModel)
            .options(selectinload(MovieCommentModel.replies))
            .where(MovieCommentModel.id == comment.id)
        )
    ).one()
    return MovieCommentSchema.model_validate(saved_comment)


@router.post(
    "/comments/{comment_id}/replies",
    response_model=MovieCommentReplySchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment_reply(
    comment_id: int,
    data: MovieCommentCreateSchema,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MovieCommentReplySchema:
    parent = await db.get(MovieCommentModel, comment_id)
    if parent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found.",
        )
    if parent.parent_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Replies cannot have nested replies.",
        )

    reply = MovieCommentModel(
        text=data.text,
        user_id=user.id,
        movie_id=parent.movie_id,
        parent_id=parent.id,
        replies=[],
    )
    db.add(reply)
    await db.commit()
    await db.refresh(reply)
    return MovieCommentReplySchema.model_validate(reply)
