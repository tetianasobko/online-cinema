import asyncio
from datetime import datetime, timezone

from sqlalchemy import delete

from database.models import ActivationTokenModel
from database.session import AsyncSQLiteSessionLocal
from tasks.celery_app import celery_app


async def delete_expired_activation_tokens_from_database() -> int:
    async with AsyncSQLiteSessionLocal() as session:
        result = await session.execute(
            delete(ActivationTokenModel).where(
                ActivationTokenModel.expires_at <= datetime.now(timezone.utc)
            )
        )
        await session.commit()
        return result.rowcount or 0


@celery_app.task(name="delete_expired_activation_tokens")
def delete_expired_activation_tokens() -> int:
    return asyncio.run(delete_expired_activation_tokens_from_database())
