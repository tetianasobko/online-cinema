from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession, async_sessionmaker
)

from config import get_settings

settings = get_settings()
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSQLiteSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSQLiteSessionLocal() as session:
        yield session
