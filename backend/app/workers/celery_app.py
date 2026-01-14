"""
Celery Application Configuration

Configures the Celery application for async task processing.
"""

from celery import Celery

from backend.app.core.config import settings


celery_app = Celery(
    "llm_judge",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["backend.app.workers.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task settings
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_TASK_TIME_LIMIT - 60,
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Result settings
    result_expires=86400,  # 24 hours

    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks

    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,

    # Rate limiting
    task_annotations={
        "backend.app.workers.tasks.run_batch_evaluation": {
            "rate_limit": "10/m"  # 10 jobs per minute max
        }
    },

    # Queues
    task_routes={
        "backend.app.workers.tasks.run_batch_evaluation": {"queue": "evaluations"},
        "backend.app.workers.tasks.run_single_evaluation": {"queue": "evaluations"},
        "backend.app.workers.tasks.cleanup_expired_data": {"queue": "maintenance"},
    }
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "cleanup-expired-data": {
        "task": "backend.app.workers.tasks.cleanup_expired_data",
        "schedule": 86400.0,  # Daily
    },
    "update-statistics-cache": {
        "task": "backend.app.workers.tasks.update_statistics_cache",
        "schedule": 3600.0,  # Hourly
    },
}
