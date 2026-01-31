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
        "app.tasks.anomaly_detection_tasks",  # BR-008: Nightly anomaly detection
        "app.tasks.batch_reprocessing_tasks",  # Phase 1: Batch reprocessing for anomaly detection
        "app.tasks.alert_backfill_tasks",  # Alert backfill batch jobs
        "app.tasks.alert_monitoring_tasks",  # Alert evaluation, escalation, monitoring
        "app.tasks.learning_tasks",  # Self-learning system tasks
        "app.tasks.forensic_audit_tasks",  # Forensic audit pipeline
        "app.tasks.market_intelligence_tasks"  # Market intelligence ingestion/refresh
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
    'recover-stuck-extractions': {
        'task': 'app.tasks.extraction_tasks.recover_stuck_extractions',
        'schedule': crontab(minute='*'),  # Every minute
        'options': {
            'expires': 60,  # Task expires after 1 minute if not picked up
        }
    },
    # Self-Learning System Tasks
    '🔥-discover-extraction-patterns': {
        'task': 'app.tasks.learning_tasks.discover_extraction_patterns',
        'schedule': crontab(hour=2, minute=30),  # 2:30 AM UTC daily (after anomaly detection)
        'options': {
            'expires': 3600,  # Task expires after 1 hour if not picked up
        }
    },
    'analyze-captured-issues': {
        'task': 'app.tasks.learning_tasks.analyze_captured_issues',
        'schedule': crontab(hour='*/6', minute=0),  # Every 6 hours
        'options': {
            'expires': 3600,  # Task expires after 1 hour if not picked up
        }
    },
    'sync-mcp-tasks': {
        'task': 'app.tasks.learning_tasks.sync_mcp_tasks',
        'schedule': crontab(hour='*/2', minute=0),  # Every 2 hours
        'options': {
            'expires': 1800,  # Task expires after 30 minutes if not picked up
        }
    },
    'cleanup-old-issues': {
        'task': 'app.tasks.learning_tasks.cleanup_old_issues',
        'schedule': crontab(hour=3, minute=0),  # 3:00 AM UTC daily
        'options': {
            'expires': 3600,  # Task expires after 1 hour if not picked up
        }
    },
    # Self-Learning Forensic Reconciliation Tasks
    'analyze-reconciliation-patterns': {
        'task': 'app.tasks.learning_tasks.analyze_reconciliation_patterns',
        'schedule': crontab(hour='*/6', minute=0),  # Every 6 hours
        'options': {
            'expires': 3600,  # Task expires after 1 hour if not picked up
        }
    },
    'update-matching-rules': {
        'task': 'app.tasks.learning_tasks.update_matching_rules',
        'schedule': crontab(hour='*/12', minute=0),  # Every 12 hours
        'options': {
            'expires': 1800,  # Task expires after 30 minutes if not picked up
        }
    },
    'train-ml-models': {
        'task': 'app.tasks.learning_tasks.train_ml_models',
        'schedule': crontab(hour=4, minute=0),  # 4:00 AM UTC daily
        'options': {
            'expires': 7200,  # Task expires after 2 hours if not picked up
        }
    },
}

# Task routing (optional - for multiple queues)
# Route forensic audit jobs to a dedicated queue to avoid backlog from other tasks.
celery_app.conf.task_routes = {
    "forensic_audit.run_complete_audit": {"queue": "forensic_audit"},
}

# OpenTelemetry: instrument Celery workers after process init (required for BatchSpanProcessor)
from celery.signals import worker_process_init


@worker_process_init.connect(weak=False)
def _init_celery_otel(*args, **kwargs):
    try:
        from app.monitoring.otel_tracing import setup_otel_celery
        setup_otel_celery()
    except Exception as e:
        import logging
        logging.getLogger(__name__).debug(f"OTel Celery init skipped: {e}")
