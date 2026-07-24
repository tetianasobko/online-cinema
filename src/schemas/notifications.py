from datetime import datetime

from pydantic import BaseModel

from database.models import NotificationTypeEnum


class NotificationSchema(BaseModel):
    id: int
    type: NotificationTypeEnum
    comment_id: int
    actor_id: int
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListSchema(BaseModel):
    notifications: list[NotificationSchema]
    page: int
    per_page: int
    total_pages: int
    total_items: int
