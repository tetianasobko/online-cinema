from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from urllib.parse import urlencode

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
