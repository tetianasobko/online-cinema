from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    CommentLikesModel,
    MovieCommentModel,
    NotificationModel,
    NotificationTypeEnum,
    UserModel,
)
from database.session import get_db
from schemas.accounts import MessageResponseSchema
from security.authorization import get_current_user


router = APIRouter()


async def _get_comment_or_404(
    comment_id: int,
    db: AsyncSession,
) -> MovieCommentModel:
    comment = await db.get(MovieCommentModel, comment_id)
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found.",
        )
    return comment


async def _comment_like_exists(
    comment_id: int,
    user_id: int,
    db: AsyncSession,
) -> bool:
    liked_comment_id = await db.scalar(
        select(CommentLikesModel.c.comment_id).where(
            CommentLikesModel.c.comment_id == comment_id,
            CommentLikesModel.c.user_id == user_id,
        )
    )
    return liked_comment_id is not None


@router.post(
    "/comments/{comment_id}/likes",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Like a comment",
    description="Like a comment and notify its author when appropriate.",
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "The comment was not found."},
        409: {"description": "The comment is already liked."},
    },
)
async def like_comment(
    comment_id: int,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponseSchema:
    comment = await _get_comment_or_404(comment_id, db)
    if await _comment_like_exists(comment_id, user.id, db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Comment is already liked.",
        )

    await db.execute(
        insert(CommentLikesModel).values(
            user_id=user.id,
            comment_id=comment_id,
        )
    )
    if comment.user_id != user.id:
        db.add(
            NotificationModel(
                type=NotificationTypeEnum.COMMENT_LIKE,
                recipient_id=comment.user_id,
                actor_id=user.id,
                comment_id=comment.id,
            )
        )
    await db.commit()
    return MessageResponseSchema(message="Comment liked.")


@router.delete(
    "/comments/{comment_id}/likes",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Remove a comment like",
    description="Remove the authenticated user's like from a comment.",
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "The comment or like was not found."},
    },
)
async def unlike_comment(
    comment_id: int,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponseSchema:
    await _get_comment_or_404(comment_id, db)
    if not await _comment_like_exists(comment_id, user.id, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment like not found.",
        )

    await db.execute(
        delete(CommentLikesModel).where(
            CommentLikesModel.c.user_id == user.id,
            CommentLikesModel.c.comment_id == comment_id,
        )
    )
    await db.commit()
    return MessageResponseSchema(message="Comment like removed.")
