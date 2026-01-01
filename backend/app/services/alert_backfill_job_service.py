"""
Alert Backfill Batch Job Service

Creates and manages batch jobs that backfill alerts across periods.
"""

from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.batch_reprocessing_job import BatchReprocessingJob
from app.models.document_upload import DocumentUpload
from app.models.financial_metrics import FinancialMetrics
from app.models.financial_period import FinancialPeriod
from app.models.property import Property

logger = logging.getLogger(__name__)


class AlertBackfillJobService:
    """Service for creating and running alert backfill batch jobs."""

    def __init__(self, db: Session):
        self.db = db

    def _build_period_query(
        self,
        property_ids: Optional[List[int]],
        date_range_start: Optional[date],
        date_range_end: Optional[date],
        document_types: Optional[List[str]]
    ):
        query = self.db.query(FinancialPeriod, FinancialMetrics).join(
            FinancialMetrics, FinancialMetrics.period_id == FinancialPeriod.id
        )

        if property_ids:
            query = query.filter(FinancialPeriod.property_id.in_(property_ids))

        if date_range_start:
            start_year = date_range_start.year
            start_month = date_range_start.month
            query = query.filter(
                or_(
                    FinancialPeriod.period_year > start_year,
                    and_(
                        FinancialPeriod.period_year == start_year,
                        FinancialPeriod.period_month >= start_month
                    )
                )
            )

        if date_range_end:
            end_year = date_range_end.year
            end_month = date_range_end.month
            query = query.filter(
                or_(
                    FinancialPeriod.period_year < end_year,
                    and_(
                        FinancialPeriod.period_year == end_year,
                        FinancialPeriod.period_month <= end_month
                    )
                )
            )

        if document_types:
            doc_periods = self.db.query(DocumentUpload.period_id).filter(
                DocumentUpload.document_type.in_(document_types),
                DocumentUpload.extraction_status == 'completed'
            )
            if property_ids:
                doc_periods = doc_periods.filter(DocumentUpload.property_id.in_(property_ids))
            query = query.filter(FinancialPeriod.id.in_(doc_periods))

        return query

    def _ensure_alert_job(self, job: BatchReprocessingJob) -> None:
        summary = job.results_summary or {}
        if summary.get("job_type") != "alert_backfill":
            raise ValueError(f"Batch job {job.id} is not an alert backfill job")

    def create_batch_job(
        self,
        user_id: int,
        property_ids: Optional[List[int]] = None,
        date_range_start: Optional[date] = None,
        date_range_end: Optional[date] = None,
        document_types: Optional[List[str]] = None,
        job_name: Optional[str] = None,
        ignore_cooldown: bool = True
    ) -> BatchReprocessingJob:
        if date_range_start and date_range_end and date_range_end < date_range_start:
            raise ValueError("date_range_end must be >= date_range_start")

        if property_ids:
            valid_properties = self.db.query(Property.id).filter(Property.id.in_(property_ids)).all()
            valid_property_ids = [p.id for p in valid_properties]
            if len(valid_property_ids) != len(property_ids):
                invalid_ids = set(property_ids) - set(valid_property_ids)
                logger.warning(f"Invalid property IDs: {invalid_ids}")

        period_query = self._build_period_query(
            property_ids=property_ids,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            document_types=document_types
        )
        total_periods = period_query.count()

        if not job_name:
            property_label = "all properties" if not property_ids else f"{len(property_ids)} properties"
            if date_range_start and date_range_end:
                range_label = f"{date_range_start.year}-{date_range_start.month:02d} to {date_range_end.year}-{date_range_end.month:02d}"
            elif date_range_start:
                range_label = f"from {date_range_start.year}-{date_range_start.month:02d}"
            elif date_range_end:
                range_label = f"through {date_range_end.year}-{date_range_end.month:02d}"
            else:
                range_label = "all periods"
            job_name = f"Alert backfill for {property_label} ({range_label})"

        batch_job = BatchReprocessingJob(
            job_name=job_name,
            initiated_by=user_id,
            property_ids=property_ids,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            document_types=document_types,
            extraction_status_filter='all',
            status='queued',
            total_documents=total_periods,
            processed_documents=0,
            successful_count=0,
            failed_count=0,
            skipped_count=0,
            results_summary={
                "job_type": "alert_backfill",
                "ignore_cooldown": ignore_cooldown
            }
        )

        self.db.add(batch_job)
        self.db.commit()
        self.db.refresh(batch_job)

        logger.info(f"Created alert backfill job {batch_job.id} with {total_periods} periods")

        return batch_job

    def start_batch_job(self, job_id: int) -> Dict[str, Any]:
        from app.tasks.alert_backfill_tasks import backfill_alerts_batch

        job = self.db.query(BatchReprocessingJob).filter(BatchReprocessingJob.id == job_id).first()

        if not job:
            raise ValueError(f"Batch job {job_id} not found")

        self._ensure_alert_job(job)

        if job.status != 'queued':
            raise ValueError(f"Batch job {job_id} is not in 'queued' status (current: {job.status})")

        task = backfill_alerts_batch.delay(job_id)

        job.celery_task_id = task.id
        job.status = 'running'
        job.started_at = datetime.now()
        self.db.commit()

        logger.info(f"Started alert backfill job {job_id} with Celery task {task.id}")

        return {
            "job_id": job.id,
            "task_id": task.id,
            "status": job.status,
            "total_documents": job.total_documents
        }

    def get_job_status(self, job_id: int) -> Dict[str, Any]:
        job = self.db.query(BatchReprocessingJob).filter(BatchReprocessingJob.id == job_id).first()

        if not job:
            raise ValueError(f"Batch job {job_id} not found")

        self._ensure_alert_job(job)

        progress_pct = 0
        if job.total_documents > 0:
            progress_pct = int((job.processed_documents / job.total_documents) * 100)

        eta = None
        if job.started_at and job.processed_documents > 0:
            now = datetime.now(job.started_at.tzinfo) if job.started_at.tzinfo else datetime.now()
            elapsed = (now - job.started_at).total_seconds()
            periods_per_second = job.processed_documents / elapsed
            remaining_periods = job.total_documents - job.processed_documents
            if periods_per_second > 0:
                eta_seconds = remaining_periods / periods_per_second
                eta = now + timedelta(seconds=eta_seconds)

        return {
            "job_id": job.id,
            "job_name": job.job_name,
            "status": job.status,
            "progress_pct": progress_pct,
            "total_documents": job.total_documents,
            "processed_documents": job.processed_documents,
            "successful_count": job.successful_count,
            "failed_count": job.failed_count,
            "skipped_count": job.skipped_count,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "estimated_completion_at": eta,
            "celery_task_id": job.celery_task_id,
            "results_summary": job.results_summary
        }

    def cancel_job(self, job_id: int) -> bool:
        from app.core.celery_config import celery_app

        job = self.db.query(BatchReprocessingJob).filter(BatchReprocessingJob.id == job_id).first()

        if not job:
            raise ValueError(f"Batch job {job_id} not found")

        self._ensure_alert_job(job)

        if job.status not in ['queued', 'running']:
            raise ValueError(f"Cannot cancel job in status: {job.status}")

        if job.celery_task_id:
            celery_app.control.revoke(job.celery_task_id, terminate=True)

        job.status = 'cancelled'
        job.completed_at = datetime.now()
        self.db.commit()

        logger.info(f"Cancelled alert backfill job {job_id}")

        return True

    def list_jobs(
        self,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[BatchReprocessingJob]:
        query = self.db.query(BatchReprocessingJob)

        job_type_expr = BatchReprocessingJob.results_summary['job_type'].astext
        query = query.filter(job_type_expr == "alert_backfill")

        if user_id:
            query = query.filter(BatchReprocessingJob.initiated_by == user_id)

        if status:
            query = query.filter(BatchReprocessingJob.status == status)

        return query.order_by(BatchReprocessingJob.created_at.desc()).limit(limit).all()
