"""
Celery application configuration.

FAANG-grade Celery setup with proper task routing, monitoring, and error handling.
"""

from celery import Celery
from celery.schedules import crontab
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# Create Celery app
celery_app = Celery(
    "scanzakup",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.ingest_workers.tasks",
    ],
)

# Configure Celery
celery_app.conf.update(
    # Task serialization
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=True,
    
    # Task routing
    task_routes=settings.CELERY_TASK_ROUTES,
    
    # Worker configuration
    worker_prefetch_multiplier=1,  # Prevent memory issues
    worker_max_tasks_per_child=1000,  # Restart workers periodically
    worker_disable_rate_limits=False,
    
    # Task configuration
    task_acks_late=True,  # Acknowledge tasks after completion
    task_reject_on_worker_lost=True,  # Retry on worker failure
    task_track_started=True,  # Track when tasks start
    task_time_limit=3600,  # 1 hour limit
    task_soft_time_limit=3300,  # 55 minutes soft limit
    
    # Result backend configuration
    result_expires=86400,  # 24 hours
    result_backend_transport_options={
        "master_name": "mymaster",
        "retry_on_timeout": True,
    },
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        # Sync all data every 30 minutes
        "sync-all-data": {
            "task": "app.ingest_workers.tasks.sync_all_data",
            "schedule": crontab(minute="*/30"),
            "options": {"queue": "ingest"},
        },
        
        # Sync delta data every 5 minutes
        "sync-delta-data": {
            "task": "app.ingest_workers.tasks.sync_delta_data",
            "schedule": crontab(minute="*/5"),
            "options": {"queue": "ingest"},
        },
        
        # Daily cleanup at 2 AM
        "cleanup-old-data": {
            "task": "app.ingest_workers.tasks.cleanup_old_data",
            "schedule": crontab(hour=2, minute=0),
            "options": {"queue": "maintenance"},
        },
        
        # Weekly health check on Sundays at 6 AM
        "health-check": {
            "task": "app.ingest_workers.tasks.health_check",
            "schedule": crontab(hour=6, minute=0, day_of_week=0),
            "options": {"queue": "monitoring"},
        },
    },
)

# Task annotations for additional configuration
celery_app.conf.task_annotations = {
    "app.ingest_workers.tasks.sync_all_data": {
        "rate_limit": "1/m",  # Max 1 per minute
        "time_limit": 3600,   # 1 hour
        "soft_time_limit": 3300,  # 55 minutes
    },
    "app.ingest_workers.tasks.sync_trd_buy_data": {
        "rate_limit": "2/m",
        "time_limit": 1800,   # 30 minutes
    },
    "app.ingest_workers.tasks.sync_lots_data": {
        "rate_limit": "2/m", 
        "time_limit": 1800,
    },
    "app.ingest_workers.tasks.sync_contracts_data": {
        "rate_limit": "2/m",
        "time_limit": 1800,
    },
    "app.ingest_workers.tasks.sync_participants_data": {
        "rate_limit": "1/h",  # Less frequent
        "time_limit": 3600,
    },
    "app.ingest_workers.tasks.cleanup_old_data": {
        "rate_limit": "1/d",  # Once per day
        "time_limit": 7200,   # 2 hours
    },
}


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    logger.info("Debug task executed", request_id=self.request.id)
    return f"Request: {self.request!r}"


# Error handling
@celery_app.task(bind=True)
def task_failure_handler(self, task_id, error, traceback):
    """Handle task failures."""
    logger.error(
        "Task failed",
        task_id=task_id,
        error=str(error),
        traceback=traceback,
    )


# Custom task base class for additional functionality
class BaseTask(celery_app.Task):
    """Base task class with custom error handling and logging."""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called on task success."""
        logger.info(
            "Task completed successfully",
            task_id=task_id,
            task_name=self.name,
            args=args,
            kwargs=kwargs,
            result=retval,
        )
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called on task failure."""
        logger.error(
            "Task failed",
            task_id=task_id,
            task_name=self.name,
            args=args,
            kwargs=kwargs,
            exception=str(exc),
            traceback=str(einfo),
        )
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called on task retry."""
        logger.warning(
            "Task retry",
            task_id=task_id,
            task_name=self.name,
            args=args,
            kwargs=kwargs,
            exception=str(exc),
            retry_count=self.request.retries,
        )


# Set the custom base task
celery_app.Task = BaseTask 