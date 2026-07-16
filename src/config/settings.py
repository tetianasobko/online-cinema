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
