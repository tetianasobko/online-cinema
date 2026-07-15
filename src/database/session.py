import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession, async_sessionmaker
)


SQLITE_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./online_cinema.db",
)

engine = create_async_engine(SQLITE_DATABASE_URL, echo=False)
AsyncSQLiteSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSQLiteSessionLocal() as session:
        yield session
