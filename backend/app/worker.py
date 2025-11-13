"""
Celery worker configuration.
"""
from celery import Celery
from loguru import logger

from .config import get_settings

settings = get_settings()

# Configure logger
logger.add(
    "logs/worker_{time}.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO"
)

# Create Celery app
celery_app = Celery(
    "video_generation",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=settings.CELERY_TASK_TRACK_STARTED,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_TASK_TIME_LIMIT - 300,  # 5 min before hard limit
    worker_prefetch_multiplier=1,  # Only take one task at a time (GPU intensive)
    worker_max_tasks_per_child=10,  # Restart worker after 10 tasks to prevent memory leaks
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
)

# Auto-discover tasks
celery_app.autodiscover_tasks(['app'])

logger.info("Celery worker configured successfully")


if __name__ == '__main__':
    celery_app.start()
