"""
Batch Reprocessing Service

Handles batch reprocessing of documents for anomaly detection.
Allows filtering by property, date range, document type, and extraction status.
"""

from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

from app.models.batch_reprocessing_job import BatchReprocessingJob
from app.models.document_upload import DocumentUpload
from app.models.property import Property

logger = logging.getLogger(__name__)


class BatchReprocessingService:
    """Service for managing batch reprocessing jobs."""

    def __init__(self, db: Session):
        self.db = db

    def create_batch_job(
        self,
        user_id: int,
        property_ids: Optional[List[int]] = None,
        date_range_start: Optional[date] = None,
        date_range_end: Optional[date] = None,
        document_types: Optional[List[str]] = None,
        extraction_status_filter: str = 'all',
        job_name: Optional[str] = None
    ) -> BatchReprocessingJob:
        """
        Create a new batch reprocessing job.

        Args:
            user_id: User initiating the job
            property_ids: Optional list of property IDs to reprocess
            date_range_start: Optional start date filter
            date_range_end: Optional end date filter
            document_types: Optional list of document types (balance_sheet, income_statement, etc.)
            extraction_status_filter: Filter by extraction status (all, completed, failed)
            job_name: Optional human-readable job name

        Returns:
            Created batch job instance
        """
        # Validate property_ids exist
        if property_ids:
            valid_properties = self.db.query(Property.id).filter(Property.id.in_(property_ids)).all()
            valid_property_ids = [p.id for p in valid_properties]
            if len(valid_property_ids) != len(property_ids):
                invalid_ids = set(property_ids) - set(valid_property_ids)
                logger.warning(f"Invalid property IDs: {invalid_ids}")

        # Query documents matching filters
        query = self.db.query(DocumentUpload)

        # Apply filters
        filters = []
        if property_ids:
            filters.append(DocumentUpload.property_id.in_(property_ids))

        if date_range_start:
            filters.append(DocumentUpload.upload_date >= date_range_start)

        if date_range_end:
            filters.append(DocumentUpload.upload_date <= date_range_end)

        if document_types:
            filters.append(DocumentUpload.document_type.in_(document_types))

        if extraction_status_filter != 'all':
            filters.append(DocumentUpload.extraction_status == extraction_status_filter)

        if filters:
            query = query.filter(and_(*filters))

        # Count total documents
        total_documents = query.count()

        # Create job name if not provided
        if not job_name:
            property_names = "all properties" if not property_ids else f"{len(property_ids)} properties"
            job_name = f"Reprocess {total_documents} documents for {property_names}"

        # Create batch job record
        batch_job = BatchReprocessingJob(
            job_name=job_name,
            initiated_by=user_id,
            property_ids=property_ids,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            document_types=document_types,
            extraction_status_filter=extraction_status_filter,
            status='queued',
            total_documents=total_documents,
            processed_documents=0,
            successful_count=0,
            failed_count=0,
            skipped_count=0
        )

        self.db.add(batch_job)
        self.db.commit()
        self.db.refresh(batch_job)

        logger.info(f"Created batch reprocessing job {batch_job.id} with {total_documents} documents")

        return batch_job

    def start_batch_job(self, job_id: int) -> Dict[str, Any]:
        """
        Start a batch reprocessing job asynchronously.

        Args:
            job_id: Batch job ID to start

        Returns:
            Job info with Celery task ID
        """
        from app.tasks.batch_reprocessing_tasks import reprocess_documents_batch

        job = self.db.query(BatchReprocessingJob).filter(BatchReprocessingJob.id == job_id).first()

        if not job:
            raise ValueError(f"Batch job {job_id} not found")

        if job.status != 'queued':
            raise ValueError(f"Batch job {job_id} is not in 'queued' status (current: {job.status})")

        # Queue Celery task
        task = reprocess_documents_batch.delay(job_id)

        # Update job with task ID
        job.celery_task_id = task.id
        job.status = 'running'
        job.started_at = datetime.now()
        self.db.commit()

        logger.info(f"Started batch job {job_id} with Celery task {task.id}")

        return {
            "job_id": job.id,
            "task_id": task.id,
            "status": job.status,
            "total_documents": job.total_documents
        }

    def get_job_status(self, job_id: int) -> Dict[str, Any]:
        """
        Get current status of batch job.

        Args:
            job_id: Batch job ID

        Returns:
            Job status information
        """
        job = self.db.query(BatchReprocessingJob).filter(BatchReprocessingJob.id == job_id).first()

        if not job:
            raise ValueError(f"Batch job {job_id} not found")

        # Calculate progress percentage
        progress_pct = 0
        if job.total_documents > 0:
            progress_pct = int((job.processed_documents / job.total_documents) * 100)

        # Calculate ETA
        eta = None
        if job.started_at and job.processed_documents > 0:
            elapsed = (datetime.now() - job.started_at).total_seconds()
            docs_per_second = job.processed_documents / elapsed
            remaining_docs = job.total_documents - job.processed_documents
            if docs_per_second > 0:
                eta_seconds = remaining_docs / docs_per_second
                eta = datetime.now() + timedelta(seconds=eta_seconds)

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
        """
        Cancel a running batch job.

        Args:
            job_id: Batch job ID to cancel

        Returns:
            True if cancelled successfully
        """
        from app.core.celery_config import celery_app

        job = self.db.query(BatchReprocessingJob).filter(BatchReprocessingJob.id == job_id).first()

        if not job:
            raise ValueError(f"Batch job {job_id} not found")

        if job.status not in ['queued', 'running']:
            raise ValueError(f"Cannot cancel job in status: {job.status}")

        # Revoke Celery task if running
        if job.celery_task_id:
            celery_app.control.revoke(job.celery_task_id, terminate=True)

        # Update job status
        job.status = 'cancelled'
        job.completed_at = datetime.now()
        self.db.commit()

        logger.info(f"Cancelled batch job {job_id}")

        return True

    def list_jobs(
        self,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[BatchReprocessingJob]:
        """
        List batch jobs with optional filters.

        Args:
            user_id: Filter by user
            status: Filter by status
            limit: Maximum number of jobs to return

        Returns:
            List of batch jobs
        """
        query = self.db.query(BatchReprocessingJob)

        if user_id:
            query = query.filter(BatchReprocessingJob.initiated_by == user_id)

        if status:
            query = query.filter(BatchReprocessingJob.status == status)

        query = query.order_by(BatchReprocessingJob.created_at.desc()).limit(limit)

        return query.all()
