from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from config import get_jwt_auth_manager
from database.models import UserGroupEnum, UserModel
from database.session import get_db
from security.exceptions import InvalidTokenError
from security.http import get_token
from security.interfaces import JWTAuthManagerInterface

ROLE_LEVELS = {
    UserGroupEnum.USER: 1,
    UserGroupEnum.MODERATOR: 2,
    UserGroupEnum.ADMIN: 3,
}


async def get_current_user(
    token: str = Depends(get_token),
    db: AsyncSession = Depends(get_db),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
) -> UserModel:
    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
    except InvalidTokenError as error:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired access token.",
        ) from error

    user = await db.scalar(
        select(UserModel)
        .options(joinedload(UserModel.group))
        .where(UserModel.id == user_id)
    )
    if user is None or not user.is_active:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired access token.",
        )
    return user


def require_role(
    required_role: UserGroupEnum,
) -> Callable[..., Coroutine[Any, Any, UserModel]]:
    async def role_checker(
        user: UserModel = Depends(get_current_user),
    ) -> UserModel:
        if ROLE_LEVELS[user.group.name] < ROLE_LEVELS[required_role]:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Insufficient permissions.",
            )
        return user

    return role_checker


require_moderator = require_role(UserGroupEnum.MODERATOR)
require_admin = require_role(UserGroupEnum.ADMIN)
