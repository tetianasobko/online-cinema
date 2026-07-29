import os
from pathlib import Path

from pydantic_settings import BaseSettings


class BaseAppSettings(BaseSettings):
    BASE_DIR: Path = Path(__file__).parent.parent

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./online_cinema.db",
    )
    LOGIN_TIME_DAYS: int = int(os.getenv("LOGIN_TIME_DAYS", 7))

    CELERY_BROKER_URL: str = os.getenv(
        "CELERY_BROKER_URL",
        "redis://localhost:6379/0",
    )

    EMAIL_HOST: str = os.getenv("EMAIL_HOST", "localhost")
    EMAIL_PORT: int = int(os.getenv("EMAIL_PORT", 1025))
    EMAIL_FROM: str = os.getenv(
        "EMAIL_FROM",
        "noreply@online-cinema.local",
    )

    STRIPE_SECRET_KEY: str = os.getenv(
        "STRIPE_SECRET_KEY",
        "change-this-stripe-secret-key",
    )
    STRIPE_WEBHOOK_SECRET: str = os.getenv(
        "STRIPE_WEBHOOK_SECRET",
        "change-this-stripe-webhook-secret",
    )
    STRIPE_SUCCESS_URL: str = os.getenv(
        "STRIPE_SUCCESS_URL",
        (
            "http://localhost:8000/api/v1/payments/success"
            "?session_id={CHECKOUT_SESSION_ID}"
        ),
    )
    STRIPE_CANCEL_URL: str = os.getenv(
        "STRIPE_CANCEL_URL",
        "http://localhost:8000/api/v1/payments/cancel",
    )
    STRIPE_CURRENCY: str = os.getenv("STRIPE_CURRENCY", "usd")


class Settings(BaseAppSettings):
    SECRET_KEY_ACCESS: str = os.getenv(
        "SECRET_KEY_ACCESS",
        "change-this-access-secret",
    )
    SECRET_KEY_REFRESH: str = os.getenv(
        "SECRET_KEY_REFRESH",
        "change-this-refresh-secret",
    )
    JWT_SIGNING_ALGORITHM: str = os.getenv(
        "JWT_SIGNING_ALGORITHM",
        "HS256",
    )
