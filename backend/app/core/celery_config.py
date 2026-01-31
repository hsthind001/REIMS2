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

# Task routing (optional - for multiple queues) - E5-S2
# Workers should consume: celery -A app.core.celery_config worker -Q extraction,analytics,forensic_audit,celery
# Extraction: high throughput; Analytics: learning, anomaly, batch; Forensic: heavy compute
celery_app.conf.task_routes = {
    "app.tasks.extraction_tasks.extract_document": {"queue": "extraction"},
    "app.tasks.extraction_tasks.batch_extract_documents": {"queue": "extraction"},
    "app.tasks.extraction_tasks.recover_stuck_extractions": {"queue": "extraction"},
    "app.tasks.anomaly_detection_tasks.run_nightly_anomaly_detection": {"queue": "analytics"},
    "app.tasks.batch_reprocessing_tasks.*": {"queue": "analytics"},
    "app.tasks.learning_tasks.*": {"queue": "analytics"},
    "app.tasks.alert_backfill_tasks.*": {"queue": "analytics"},
    "app.tasks.alert_monitoring_tasks.*": {"queue": "analytics"},
    "app.tasks.market_intelligence_tasks.*": {"queue": "analytics"},
    "forensic_audit.run_complete_audit": {"queue": "forensic_audit"},
}

# E5-S2: Dead-letter queue for failed tasks (after max retries)
# Failed task metadata is appended to Redis list "celery:dlq" for inspection/recovery.
celery_app.conf.task_reject_on_worker_lost = True  # Requeue if worker dies
celery_app.conf.task_acks_late = True  # Ack only after task completes (already set above)


def _dlq_record_failure(task_id: str, task_name: str, args: tuple, kwargs: dict, einfo: str) -> None:
    """Append failed task metadata to Redis DLQ list for later inspection."""
    try:
        from app.db.redis_client import get_redis
        from datetime import datetime
        import json
        redis_client = get_redis()
        record = {
            "task_id": task_id,
            "task_name": task_name,
            "args": str(args)[:500],
            "kwargs": str(kwargs)[:500],
            "error": str(einfo)[:1000],
            "failed_at": datetime.utcnow().isoformat(),
        }
        redis_client.lpush("celery:dlq", json.dumps(record))
        redis_client.ltrim("celery:dlq", 0, 999)  # Keep last 1000 entries
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"DLQ record failed: {e}")


from celery.signals import task_failure

@task_failure.connect
def _on_task_failure(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **kw):
    """E5-S2: Record failed tasks to DLQ for inspection."""
    if sender and task_id:
        _dlq_record_failure(
            task_id=task_id,
            task_name=sender.name if hasattr(sender, 'name') else str(sender),
            args=args or (),
            kwargs=kwargs or {},
            einfo=str(einfo) if einfo else str(exception) if exception else "unknown",
        )

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
