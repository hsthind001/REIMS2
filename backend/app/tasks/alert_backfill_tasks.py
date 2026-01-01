"""
Alert Backfill Celery Tasks

Runs alert backfill batch jobs over historical periods.
"""

from datetime import datetime
import logging

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from app.core.celery_config import celery_app
from app.db.database import SessionLocal
from app.models.batch_reprocessing_job import BatchReprocessingJob
from app.models.financial_period import FinancialPeriod
from app.services.alert_backfill_job_service import AlertBackfillJobService
from app.services.alert_trigger_service import AlertTriggerService

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task with database session management."""

    _db = None

    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def is_aborted(self) -> bool:
        request = getattr(self, "request", None)
        if not request:
            return False
        if getattr(request, "is_revoked", False):
            return True
        task_id = getattr(request, "id", None)
        if not task_id:
            return False
        return celery_app.AsyncResult(task_id).state == "REVOKED"

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(
    name="app.tasks.alert_backfill_tasks.backfill_alerts_batch",
    bind=True,
    base=DatabaseTask,
    time_limit=3600,
    soft_time_limit=3300
)
def backfill_alerts_batch(self, job_id: int):
    db = SessionLocal()
    try:
        job = db.query(BatchReprocessingJob).filter(BatchReprocessingJob.id == job_id).first()

        if not job:
            logger.error(f"Alert backfill job {job_id} not found")
            return {"status": "error", "message": f"Job {job_id} not found"}

        if job.status != 'running':
            logger.warning(f"Alert backfill job {job_id} is not running (current: {job.status})")
            return {"status": "error", "message": f"Job {job_id} is not running"}

        summary = dict(job.results_summary or {})
        if summary.get("job_type") != "alert_backfill":
            logger.error(f"Job {job_id} is not an alert backfill job")
            job.status = 'failed'
            job.completed_at = datetime.now()
            summary.update({"error": "Invalid job type"})
            job.results_summary = summary
            db.commit()
            return {"status": "error", "message": "Invalid job type"}

        ignore_cooldown = bool(summary.get("ignore_cooldown", True))

        service = AlertBackfillJobService(db)
        period_query = service._build_period_query(
            property_ids=job.property_ids,
            date_range_start=job.date_range_start,
            date_range_end=job.date_range_end,
            document_types=job.document_types
        )
        period_rows = period_query.order_by(
            FinancialPeriod.property_id,
            FinancialPeriod.period_year,
            FinancialPeriod.period_month
        ).all()

        if len(period_rows) != job.total_documents:
            logger.warning(
                f"Period count mismatch for job {job_id}: expected {job.total_documents}, found {len(period_rows)}"
            )

        chunk_size = 25
        total_processed = 0
        successful = 0
        failed = 0
        skipped = 0
        alerts_created = 0
        error_details = []

        trigger_service = AlertTriggerService(db)

        for i in range(0, len(period_rows), chunk_size):
            chunk = period_rows[i:i + chunk_size]

            if self.is_aborted():
                logger.info(f"Task revoked for job {job_id}, stopping processing")
                job.status = 'cancelled'
                job.completed_at = datetime.now()
                db.commit()
                return {"status": "cancelled", "processed": total_processed}

            for period, metrics in chunk:
                try:
                    if not metrics:
                        skipped += 1
                        total_processed += 1
                        error_details.append({
                            "period_id": period.id,
                            "property_id": period.property_id,
                            "reason": "Missing metrics",
                            "type": "validation"
                        })
                        continue

                    alerts = trigger_service.evaluate_and_trigger_alerts(
                        property_id=period.property_id,
                        period_id=period.id,
                        metrics=metrics,
                        ignore_cooldown=ignore_cooldown
                    )

                    alerts_created += len(alerts)
                    db.commit()
                    successful += 1
                    total_processed += 1

                except Exception as e:
                    logger.error(
                        f"Error backfilling alerts for property {period.property_id}, period {period.id}: {str(e)}",
                        exc_info=True
                    )
                    failed += 1
                    total_processed += 1
                    error_details.append({
                        "period_id": period.id,
                        "property_id": period.property_id,
                        "reason": str(e),
                        "type": "error"
                    })
                    db.rollback()

            job.processed_documents = total_processed
            job.successful_count = successful
            job.failed_count = failed
            job.skipped_count = skipped
            job.updated_at = datetime.now()
            db.commit()

            progress_pct = int((total_processed / job.total_documents) * 100) if job.total_documents > 0 else 0
            self.update_state(
                state="PROCESSING",
                meta={
                    "job_id": job_id,
                    "progress": progress_pct,
                    "processed": total_processed,
                    "total": job.total_documents,
                    "successful": successful,
                    "failed": failed
                }
            )

            logger.info(f"Alert backfill job {job_id} progress: {total_processed}/{job.total_documents} ({progress_pct}%)")

        job.status = 'completed'
        job.completed_at = datetime.now()
        summary.update({
            "periods_evaluated": total_processed,
            "alerts_created": alerts_created,
            "successful": successful,
            "failed": failed,
            "skipped": skipped,
            "completion_time": datetime.now().isoformat(),
            "error_details": error_details[:100]
        })
        job.results_summary = summary
        db.commit()

        logger.info(
            f"Completed alert backfill job {job_id}: {alerts_created} alerts created across {total_processed} periods"
        )

        return {
            "status": "completed",
            "job_id": job_id,
            "periods_evaluated": total_processed,
            "alerts_created": alerts_created,
            "successful": successful,
            "failed": failed,
            "skipped": skipped
        }

    except SoftTimeLimitExceeded:
        logger.warning(f"Soft time limit exceeded for alert backfill job {job_id}")
        job = db.query(BatchReprocessingJob).filter(BatchReprocessingJob.id == job_id).first()
        if job:
            summary = dict(job.results_summary or {})
            job.status = 'failed'
            job.completed_at = datetime.now()
            summary.update({"error": "Time limit exceeded"})
            job.results_summary = summary
            db.commit()
        return {"status": "timeout", "message": "Processing time limit exceeded"}

    except Exception as e:
        logger.error(f"Error in alert backfill job {job_id}: {str(e)}", exc_info=True)
        job = db.query(BatchReprocessingJob).filter(BatchReprocessingJob.id == job_id).first()
        if job:
            summary = dict(job.results_summary or {})
            job.status = 'failed'
            job.completed_at = datetime.now()
            summary.update({"error": str(e)})
            job.results_summary = summary
            db.commit()
        return {"status": "error", "message": str(e)}

    finally:
        db.close()
