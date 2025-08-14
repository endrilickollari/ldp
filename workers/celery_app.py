from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["workers.tasks"]
)

celery_app.conf.update(
    task_track_started=True,
    task_acks_late=True,
    broker_connection_retry_on_startup=True
)
