from datetime import datetime, timezone
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from config import Settings, get_jwt_auth_manager, get_settings
from database.models import (
    ActivationTokenModel,
    PasswordResetTokenModel,
    RefreshTokenModel,
    UserGroupEnum,
    UserGroupModel,
    UserModel,
)
from database.session import get_db
from notifications import EmailSenderInterface, get_email_sender
from security import (
    JWTAuthManagerInterface,
    hash_password,
    verify_password,
)
from security.exceptions import InvalidTokenError
from security.authorization import require_admin
from security.http import get_token
import schemas


router = APIRouter()
ACTIVATION_RESEND_MESSAGE = (
    "If the account can be activated, a new activation link has been sent."
)
PASSWORD_RESET_MESSAGE = (
    "If the account is registered and active, "
    "a password reset link has been sent."
)


@router.post(
    "/register",
    response_model=schemas.UserRegistrationResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Register a user",
    description=(
        "Create an inactive user account and send a 24-hour activation link "
        "to the supplied email address."
    ),
    responses={
        409: {"description": "An account with this email already exists."},
        500: {"description": "The account could not be created."},
    },
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
    summary="Activate a user account",
    description=(
        "Activate an account using the email address and token contained in "
        "the activation link."
    ),
    responses={
        400: {
            "description": (
                "The activation token is invalid or expired, or the account "
                "is already active."
            )
        },
    },
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


@router.post(
    "/activation/resend",
    response_model=schemas.MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Resend an activation link",
    description=(
        "Request a new 24-hour activation link. The response does not reveal "
        "whether the email belongs to an inactive account."
    ),
    responses={
        500: {"description": "A new activation token could not be created."},
    },
)
async def resend_activation_link(
    data: schemas.ActivationResendRequestSchema,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(get_email_sender),
) -> schemas.MessageResponseSchema:
    user = await db.scalar(
        select(UserModel)
        .options(joinedload(UserModel.activation_token))
        .where(UserModel.email == str(data.email))
    )

    if user is None or user.is_active:
        return schemas.MessageResponseSchema(
            message=ACTIVATION_RESEND_MESSAGE
        )

    if user.activation_token is not None:
        await db.delete(user.activation_token)
        await db.flush()

    token = ActivationTokenModel(user_id=user.id)
    db.add(token)

    try:
        await db.flush()
        await db.commit()
    except Exception as error:
        await db.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Something went wrong. Try again later.",
        ) from error

    query = urlencode({"email": user.email, "token": token.token})
    activation_link = (
        f"http://127.0.0.1:8000/api/v1/accounts/activate?{query}"
    )
    background_tasks.add_task(
        email_sender.send_activation_email,
        user.email,
        activation_link,
    )

    return schemas.MessageResponseSchema(
        message=ACTIVATION_RESEND_MESSAGE
    )


@router.post(
    "/login",
    response_model=schemas.UserLoginResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Log in",
    description=(
        "Authenticate an active user and return an access token and a "
        "refresh token."
    ),
    responses={
        401: {"description": "The email or password is incorrect."},
        403: {"description": "The account has not been activated."},
        500: {"description": "The refresh token could not be stored."},
    },
)
async def login_user(
    data: schemas.UserLoginRequestSchema,
    db: AsyncSession = Depends(get_db),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
    settings: Settings = Depends(get_settings),
) -> schemas.UserLoginResponseSchema:
    user = await db.scalar(
        select(UserModel).where(UserModel.email == str(data.email))
    )

    if user is None or not verify_password(
        data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "User account is not activated.",
        )

    refresh_jwt = jwt_manager.create_refresh_token({"user_id": user.id})
    refresh_token = RefreshTokenModel.create(
        user_id=user.id,
        days_valid=settings.LOGIN_TIME_DAYS,
        token=refresh_jwt,
    )
    db.add(refresh_token)

    try:
        await db.commit()
    except Exception as error:
        await db.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Something went wrong. Try again later.",
        ) from error

    access_token = jwt_manager.create_access_token({"user_id": user.id})
    return schemas.UserLoginResponseSchema(
        access_token=access_token,
        refresh_token=refresh_jwt,
    )


@router.post(
    "/logout",
    response_model=schemas.MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Log out",
    description=(
        "Delete the supplied refresh token so it can no longer be used to "
        "obtain access tokens."
    ),
    responses={
        401: {"description": "The refresh token does not exist."},
        500: {"description": "The refresh token could not be deleted."},
    },
)
async def logout_user(
    data: schemas.UserLogoutRequestSchema,
    db: AsyncSession = Depends(get_db),
) -> schemas.MessageResponseSchema:
    refresh_token = await db.scalar(
        select(RefreshTokenModel).where(
            RefreshTokenModel.token == data.refresh_token
        )
    )

    if refresh_token is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Refresh token not found.",
        )

    try:
        await db.delete(refresh_token)
        await db.commit()
    except Exception as error:
        await db.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Something went wrong. Try again later.",
        ) from error

    return schemas.MessageResponseSchema(
        message="Logged out successfully."
    )


@router.post(
    "/refresh",
    response_model=schemas.TokenRefreshResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Refresh an access token",
    description=(
        "Validate a stored refresh token and issue a new short-lived access "
        "token for an active account."
    ),
    responses={
        401: {
            "description": (
                "The refresh token is invalid, expired, revoked, or belongs "
                "to an unavailable account."
            )
        },
    },
)
async def refresh_access_token(
    data: schemas.TokenRefreshRequestSchema,
    db: AsyncSession = Depends(get_db),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
) -> schemas.TokenRefreshResponseSchema:
    try:
        payload = jwt_manager.decode_refresh_token(data.refresh_token)
        user_id = payload.get("user_id")
    except InvalidTokenError as error:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired refresh token.",
        ) from error

    stored_token = await db.scalar(
        select(RefreshTokenModel).where(
            RefreshTokenModel.token == data.refresh_token
        )
    )
    if stored_token is None or stored_token.user_id != user_id:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Refresh token not found.",
        )

    user = await db.scalar(
        select(UserModel).where(
            UserModel.id == user_id,
            UserModel.is_active.is_(True),
        )
    )
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "User account is unavailable.",
        )

    access_token = jwt_manager.create_access_token({"user_id": user.id})
    return schemas.TokenRefreshResponseSchema(
        access_token=access_token
    )


@router.post(
    "/password/change",
    response_model=schemas.MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Change a password",
    description=(
        "Change the authenticated user's password after verifying the current "
        "password."
    ),
    responses={
        400: {"description": "The current password is incorrect."},
        401: {"description": "The access token is missing, invalid, or expired."},
        500: {"description": "The password change could not be saved."},
    },
)
async def change_password(
    data: schemas.PasswordChangeRequestSchema,
    token: str = Depends(get_token),
    db: AsyncSession = Depends(get_db),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
) -> schemas.MessageResponseSchema:
    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
    except InvalidTokenError as error:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired access token.",
        ) from error

    current_user = await db.scalar(
        select(UserModel).where(UserModel.id == user_id)
    )
    if current_user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired access token.",
        )

    if not verify_password(
        data.old_password,
        current_user.hashed_password,
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Old password is incorrect.",
        )

    current_user.hashed_password = hash_password(data.new_password)
    try:
        await db.commit()
    except Exception as error:
        await db.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Something went wrong. Try again later.",
        ) from error

    return schemas.MessageResponseSchema(
        message="Password changed successfully."
    )


@router.post(
    "/password/reset/request",
    response_model=schemas.MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Request a password reset",
    description=(
        "Send a password-reset link when the email belongs to an active "
        "account. The response does not reveal whether the account exists."
    ),
    responses={
        500: {"description": "A password-reset token could not be created."},
    },
)
async def request_password_reset(
    data: schemas.PasswordResetRequestSchema,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(get_email_sender),
) -> schemas.MessageResponseSchema:
    user = await db.scalar(
        select(UserModel)
        .options(joinedload(UserModel.password_reset_token))
        .where(UserModel.email == str(data.email))
    )

    if user is None or not user.is_active:
        return schemas.MessageResponseSchema(
            message=PASSWORD_RESET_MESSAGE
        )

    try:
        if user.password_reset_token is not None:
            await db.delete(user.password_reset_token)
            await db.flush()

        reset_token = PasswordResetTokenModel(user_id=user.id)
        db.add(reset_token)
        await db.flush()
        await db.commit()
    except Exception as error:
        await db.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Something went wrong. Try again later.",
        ) from error

    query = urlencode({"email": user.email, "token": reset_token.token})
    reset_link = (
        "http://127.0.0.1:8000/api/v1/accounts/password/reset/complete"
        f"?{query}"
    )
    background_tasks.add_task(
        email_sender.send_password_reset_email,
        user.email,
        reset_link,
    )

    return schemas.MessageResponseSchema(
        message=PASSWORD_RESET_MESSAGE
    )


@router.post(
    "/password/reset/complete",
    response_model=schemas.MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Complete a password reset",
    description=(
        "Set a new password using a valid reset token and revoke all existing "
        "refresh tokens for the account."
    ),
    responses={
        400: {"description": "The password-reset token is invalid or expired."},
        500: {"description": "The new password could not be saved."},
    },
)
async def complete_password_reset(
    data: schemas.PasswordResetCompleteRequestSchema,
    db: AsyncSession = Depends(get_db),
) -> schemas.MessageResponseSchema:
    reset_token = await db.scalar(
        select(PasswordResetTokenModel)
        .options(joinedload(PasswordResetTokenModel.user))
        .join(UserModel)
        .where(
            UserModel.email == str(data.email),
            PasswordResetTokenModel.token == data.token,
            UserModel.is_active.is_(True),
        )
    )

    if reset_token is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Invalid or expired password reset token.",
        )

    expires_at = reset_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= datetime.now(timezone.utc):
        await db.delete(reset_token)
        await db.commit()
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Invalid or expired password reset token.",
        )

    user = reset_token.user
    user.hashed_password = hash_password(data.new_password)

    try:
        await db.delete(reset_token)
        await db.execute(
            delete(RefreshTokenModel).where(
                RefreshTokenModel.user_id == user.id
            )
        )
        await db.commit()
    except Exception as error:
        await db.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Something went wrong. Try again later.",
        ) from error

    return schemas.MessageResponseSchema(
        message="Password reset successfully."
    )


@router.patch(
    "/admin/users/{user_id}/group",
    response_model=schemas.MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Change a user's group",
    description=(
        "Allow an administrator to assign the user, moderator, or admin group "
        "to an existing account."
    ),
    responses={
        401: {"description": "Authentication is required."},
        403: {"description": "Administrator access is required."},
        404: {"description": "The user or requested group was not found."},
        500: {"description": "The group change could not be saved."},
    },
)
async def update_user_group(
    user_id: int,
    data: schemas.UserGroupUpdateSchema,
    _: UserModel = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> schemas.MessageResponseSchema:
    user = await db.scalar(
        select(UserModel).where(UserModel.id == user_id)
    )
    if user is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "User not found.",
        )

    group = await db.scalar(
        select(UserGroupModel).where(UserGroupModel.name == data.group)
    )
    if group is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "User group not found.",
        )

    user.group_id = group.id
    try:
        await db.commit()
    except Exception as error:
        await db.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Something went wrong. Try again later.",
        ) from error

    return schemas.MessageResponseSchema(
        message=f"User group changed to {data.group.value}."
    )


@router.post(
    "/admin/users/{user_id}/activate",
    response_model=schemas.MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Activate a user as an administrator",
    description=(
        "Allow an administrator to activate an account manually and remove "
        "its outstanding activation token."
    ),
    responses={
        401: {"description": "Authentication is required."},
        403: {"description": "Administrator access is required."},
        404: {"description": "The user was not found."},
        500: {"description": "The account could not be activated."},
    },
)
async def activate_user_by_admin(
    user_id: int,
    _: UserModel = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> schemas.MessageResponseSchema:
    user = await db.scalar(
        select(UserModel).where(UserModel.id == user_id)
    )
    if user is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "User not found.",
        )

    user.is_active = True
    try:
        await db.execute(
            delete(ActivationTokenModel).where(
                ActivationTokenModel.user_id == user.id
            )
        )
        await db.commit()
    except Exception as error:
        await db.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Something went wrong. Try again later.",
        ) from error

    return schemas.MessageResponseSchema(
        message="User account activated successfully."
    )
