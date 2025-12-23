"""
Batch Reprocessing Celery Tasks

Handles async batch reprocessing of documents for anomaly detection.
"""

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from app.core.celery_config import celery_app
from app.db.database import SessionLocal
from app.models.batch_reprocessing_job import BatchReprocessingJob
from app.models.document_upload import DocumentUpload
from app.services.extraction_orchestrator import ExtractionOrchestrator
from sqlalchemy import and_
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task with database session management"""
    _db = None

    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(
    name="app.tasks.batch_reprocessing_tasks.reprocess_documents_batch",
    bind=True,
    base=DatabaseTask,
    time_limit=3600,  # 60 minutes hard limit
    soft_time_limit=3300  # 55 minutes soft limit
)
def reprocess_documents_batch(self, job_id: int):
    """
    Celery task: Batch reprocess documents for anomaly detection.
    
    Processes documents in chunks of 10, updating job progress after each chunk.
    Handles errors gracefully and continues processing remaining documents.
    
    Args:
        job_id: BatchReprocessingJob ID
    
    Returns:
        dict: Processing summary with counts
    """
    db = SessionLocal()
    try:
        # Get batch job
        job = db.query(BatchReprocessingJob).filter(BatchReprocessingJob.id == job_id).first()
        
        if not job:
            logger.error(f"Batch job {job_id} not found")
            return {"status": "error", "message": f"Job {job_id} not found"}
        
        if job.status != 'running':
            logger.warning(f"Batch job {job_id} is not in 'running' status (current: {job.status})")
            return {"status": "error", "message": f"Job {job_id} is not running"}
        
        logger.info(f"Starting batch reprocessing for job {job_id}: {job.total_documents} documents")
        
        # Query documents matching filters
        query = db.query(DocumentUpload)
        
        # Apply filters (same as in service)
        filters = []
        if job.property_ids:
            filters.append(DocumentUpload.property_id.in_(job.property_ids))
        
        if job.date_range_start:
            filters.append(DocumentUpload.upload_date >= job.date_range_start)
        
        if job.date_range_end:
            filters.append(DocumentUpload.upload_date <= job.date_range_end)
        
        if job.document_types:
            filters.append(DocumentUpload.document_type.in_(job.document_types))
        
        if job.extraction_status_filter != 'all':
            filters.append(DocumentUpload.extraction_status == job.extraction_status_filter)
        
        if filters:
            query = query.filter(and_(*filters))
        
        # Get all document IDs
        documents = query.order_by(DocumentUpload.id).all()
        
        if len(documents) != job.total_documents:
            logger.warning(f"Document count mismatch: expected {job.total_documents}, found {len(documents)}")
        
        # Process in chunks
        chunk_size = 10
        total_processed = 0
        successful = 0
        failed = 0
        skipped = 0
        error_details = []  # Track specific error reasons
        
        # Initialize orchestrator for anomaly detection
        orchestrator = ExtractionOrchestrator(db)
        
        # Import for validation
        from app.models.financial_period import FinancialPeriod
        
        for i in range(0, len(documents), chunk_size):
            chunk = documents[i:i + chunk_size]
            
            # Check if task was revoked
            if self.is_aborted():
                logger.info(f"Task revoked for job {job_id}, stopping processing")
                job.status = 'cancelled'
                job.completed_at = datetime.now()
                db.commit()
                return {"status": "cancelled", "processed": total_processed}
            
            # Process chunk
            for doc in chunk:
                try:
                    # Pre-validate document before processing
                    validation_error = None
                    
                    # Check extraction status
                    if doc.extraction_status != 'completed':
                        validation_error = f"Extraction status is '{doc.extraction_status}', not 'completed'"
                    
                    # Check period_id exists
                    elif not doc.period_id:
                        validation_error = "Missing period_id"
                    
                    # Check period exists in database
                    elif not db.query(FinancialPeriod).filter(FinancialPeriod.id == doc.period_id).first():
                        validation_error = f"Period {doc.period_id} not found in database"
                    
                    # Skip if validation fails
                    if validation_error:
                        logger.warning(f"Document {doc.id} ({doc.file_name}): Skipping - {validation_error}")
                        skipped += 1
                        total_processed += 1
                        error_details.append({
                            "document_id": doc.id,
                            "file_name": doc.file_name,
                            "reason": validation_error,
                            "type": "validation"
                        })
                        continue
                    
                    # Trigger anomaly detection for this document
                    orchestrator._detect_anomalies_for_document(doc)
                    db.commit()  # Commit after each successful detection
                    
                    successful += 1
                    total_processed += 1
                    
                except ValueError as e:
                    # Validation errors - skip document
                    logger.warning(f"Document {doc.id} ({doc.file_name}): Validation error - {str(e)}")
                    skipped += 1
                    total_processed += 1
                    error_details.append({
                        "document_id": doc.id,
                        "file_name": doc.file_name,
                        "reason": str(e),
                        "type": "validation"
                    })
                    db.rollback()  # Rollback any partial changes
                    continue
                    
                except Exception as e:
                    # Unexpected errors - mark as failed
                    error_msg = f"Document {doc.id} ({doc.file_name}): Processing error - {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    failed += 1
                    total_processed += 1
                    error_details.append({
                        "document_id": doc.id,
                        "file_name": doc.file_name,
                        "reason": str(e),
                        "type": "error"
                    })
                    db.rollback()  # Rollback any partial changes
                    # Continue with next document
            
            # Update job progress after each chunk
            job.processed_documents = total_processed
            job.successful_count = successful
            job.failed_count = failed
            job.skipped_count = skipped
            job.updated_at = datetime.now()
            db.commit()
            
            # Update task state
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
            
            logger.info(f"Job {job_id} progress: {total_processed}/{job.total_documents} ({progress_pct}%)")
        
        # Mark job as completed
        job.status = 'completed'
        job.completed_at = datetime.now()
        job.results_summary = {
            "total_processed": total_processed,
            "successful": successful,
            "failed": failed,
            "skipped": skipped,
            "completion_time": datetime.now().isoformat(),
            "error_details": error_details[:100]  # Store first 100 errors to avoid bloat
        }
        db.commit()
        
        logger.info(f"Completed batch job {job_id}: {successful} successful, {failed} failed, {skipped} skipped")
        
        # Log summary of error types
        if error_details:
            validation_errors = [e for e in error_details if e.get("type") == "validation"]
            processing_errors = [e for e in error_details if e.get("type") == "error"]
            logger.info(f"Error breakdown: {len(validation_errors)} validation errors, {len(processing_errors)} processing errors")
        
        return {
            "status": "completed",
            "job_id": job_id,
            "total_processed": total_processed,
            "successful": successful,
            "failed": failed,
            "skipped": skipped,
            "error_summary": {
                "validation_errors": len([e for e in error_details if e.get("type") == "validation"]),
                "processing_errors": len([e for e in error_details if e.get("type") == "error"])
            }
        }
        
    except SoftTimeLimitExceeded:
        logger.warning(f"Soft time limit exceeded for job {job_id}")
        job = db.query(BatchReprocessingJob).filter(BatchReprocessingJob.id == job_id).first()
        if job:
            job.status = 'failed'
            job.completed_at = datetime.now()
            job.results_summary = {"error": "Time limit exceeded"}
            db.commit()
        return {"status": "timeout", "message": "Processing time limit exceeded"}
    
    except Exception as e:
        logger.error(f"Error in batch reprocessing job {job_id}: {str(e)}", exc_info=True)
        job = db.query(BatchReprocessingJob).filter(BatchReprocessingJob.id == job_id).first()
        if job:
            job.status = 'failed'
            job.completed_at = datetime.now()
            job.results_summary = {"error": str(e)}
            db.commit()
        return {"status": "error", "message": str(e)}
    
    finally:
        db.close()

