from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import NotificationModel, UserModel
from database.session import get_db
from schemas.accounts import MessageResponseSchema
from schemas.notifications import NotificationListSchema, NotificationSchema
from security.authorization import get_current_user


router = APIRouter()


@router.get(
    "/",
    response_model=NotificationListSchema,
    status_code=status.HTTP_200_OK,
)
async def get_notifications(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=50),
    unread_only: bool = Query(default=False),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationListSchema:
    conditions = [NotificationModel.recipient_id == user.id]
    if unread_only:
        conditions.append(NotificationModel.is_read.is_(False))

    total_items = await db.scalar(
        select(func.count(NotificationModel.id)).where(*conditions)
    ) or 0
    statement = (
        select(NotificationModel)
        .where(*conditions)
        .order_by(
            NotificationModel.created_at.desc(),
            NotificationModel.id.desc(),
        )
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    notifications = list((await db.scalars(statement)).all())

    return NotificationListSchema(
        notifications=[
            NotificationSchema.model_validate(notification)
            for notification in notifications
        ],
        page=page,
        per_page=per_page,
        total_pages=ceil(total_items / per_page) if total_items else 0,
        total_items=total_items,
    )


@router.patch(
    "/read-all",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def mark_all_notifications_as_read(
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponseSchema:
    await db.execute(
        update(NotificationModel)
        .where(
            NotificationModel.recipient_id == user.id,
            NotificationModel.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await db.commit()
    return MessageResponseSchema(message="All notifications marked as read.")


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationSchema,
    status_code=status.HTTP_200_OK,
)
async def mark_notification_as_read(
    notification_id: int,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationSchema:
    notification = await db.scalar(
        select(NotificationModel).where(
            NotificationModel.id == notification_id,
            NotificationModel.recipient_id == user.id,
        )
    )
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    if not notification.is_read:
        notification.is_read = True
        await db.commit()

    return NotificationSchema.model_validate(notification)
