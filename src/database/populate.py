from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import UserGroupEnum, UserGroupModel


async def seed_user_groups(db: AsyncSession) -> None:
    existing_groups = set(
        await db.scalars(select(UserGroupModel.name))
    )
    missing_groups = [
        UserGroupModel(name=group)
        for group in UserGroupEnum
        if group not in existing_groups
    ]

    if missing_groups:
        db.add_all(missing_groups)
        await db.commit()
