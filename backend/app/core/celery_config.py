from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "reims",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.example_tasks",
        "app.tasks.extraction_tasks",
        "app.tasks.anomaly_detection_tasks"  # BR-008: Nightly anomaly detection
    ]
)

# Celery configuration - optimized for performance
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    result_expires=3600,  # 1 hour
    # Performance optimizations
    worker_concurrency=4,  # Match CPU cores for optimal throughput
    task_acks_late=True,  # Ensure task completion before acknowledgment
    task_reject_on_worker_lost=True,  # Requeue tasks if worker dies
    task_default_rate_limit='10/m',  # Prevent overwhelming database
)

# BR-008: Nightly batch job schedule (Celery Beat)
celery_app.conf.beat_schedule = {
    'nightly-anomaly-detection': {
        'task': 'app.tasks.anomaly_detection_tasks.run_nightly_anomaly_detection',
        'schedule': crontab(hour=2, minute=0),  # 2:00 AM UTC daily
        'options': {
            'expires': 3600,  # Task expires after 1 hour if not picked up
        }
    },
}

# Task routing (optional - for multiple queues)
# DISABLED: Worker only listens to default "celery" queue
# All tasks now use default queue for immediate processing
# celery_app.conf.task_routes = {
#     "app.tasks.example_tasks.send_email": {"queue": "email"},
#     "app.tasks.example_tasks.process_data": {"queue": "default"},
#     "app.tasks.extraction_tasks.extract_document": {"queue": "extraction"},
#     "app.tasks.extraction_tasks.retry_failed_extraction": {"queue": "extraction"},
#     "app.tasks.extraction_tasks.batch_extract_documents": {"queue": "extraction"},
# }

