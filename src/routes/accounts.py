from datetime import datetime, timezone
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database.models import (
    ActivationTokenModel,
    UserGroupEnum,
    UserGroupModel,
    UserModel,
)
from database.session import get_db
from notifications import EmailSenderInterface, get_email_sender
from security import hash_password
import schemas


router = APIRouter()


@router.post(
    "/register",
    response_model=schemas.UserRegistrationResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    data: schemas.UserRegistrationRequestSchema,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(get_email_sender),
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

    query = urlencode({"email": user.email, "token": token.token})
    activation_link = f"http://127.0.0.1:8000/api/v1/accounts/activate?{query}"
    background_tasks.add_task(
        email_sender.send_activation_email,
        user.email,
        activation_link,
    )

    return user


@router.get(
    "/activate",
    response_model=schemas.MessageResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def activate_account(
    activation_data: Annotated[
        schemas.UserActivationRequestSchema,
        Depends(),
    ],
    db: AsyncSession = Depends(get_db),
) -> schemas.MessageResponseSchema:
    activation_token = await db.scalar(
        select(ActivationTokenModel)
        .options(joinedload(ActivationTokenModel.user))
        .join(UserModel)
        .where(
            UserModel.email == str(activation_data.email),
            ActivationTokenModel.token == activation_data.token,
        )
    )

    if activation_token is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Invalid or expired activation token.",
        )

    expires_at = activation_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= datetime.now(timezone.utc):
        await db.delete(activation_token)
        await db.commit()
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Invalid or expired activation token.",
        )

    user = activation_token.user
    if user.is_active:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "User account is already active.",
        )

    user.is_active = True
    await db.delete(activation_token)
    await db.commit()

    return schemas.MessageResponseSchema(
        message="User account activated successfully."
    )
