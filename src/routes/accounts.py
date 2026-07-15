from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import (
    ActivationTokenModel,
    UserGroupEnum,
    UserGroupModel,
    UserModel,
)
from database.session import get_db
from security import hash_password
import schemas


router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])


@router.post(
    "/register",
    response_model=schemas.UserRegistrationResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    data: schemas.UserRegistrationRequestSchema,
    db: AsyncSession = Depends(get_db),
) -> UserModel:
    email = str(data.email)
    if await db.scalar(select(UserModel).where(UserModel.email == email)):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A user with this email already exists."
        )

    group = await db.scalar(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    )
    if group is None:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Default user group not found."
        )

    user = UserModel(
        email=email,
        hashed_password=hash_password(data.password),
        group_id=group.id,
    )
    db.add(user)
    try:
        await db.flush()
        token = ActivationTokenModel(user_id=user.id)
        db.add(token)
        await db.flush()
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Something went wrong. Try again later."
        ) from e

    return user
