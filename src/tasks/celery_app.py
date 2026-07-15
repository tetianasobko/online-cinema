import os
from celery import Celery


celery_app = Celery(
    "online_cinema",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    include=["tasks.activation_tokens"],
)

celery_app.conf.beat_schedule = {
    "delete-expired-activation-tokens": {
        "task": "delete_expired_activation_tokens",
        "schedule": 3600.0,
    },
}
