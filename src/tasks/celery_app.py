from celery import Celery

from config import get_settings

settings = get_settings()
celery_app = Celery(
    "online_cinema",
    broker=settings.CELERY_BROKER_URL,
    include=["tasks.activation_tokens"],
)

celery_app.conf.beat_schedule = {
    "delete-expired-activation-tokens": {
        "task": "delete_expired_activation_tokens",
        "schedule": 3600.0,
    },
}
