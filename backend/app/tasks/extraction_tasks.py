"""
Celery Tasks for Document Extraction
"""
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from app.core.celery_config import celery_app
from app.db.database import SessionLocal
from app.services.extraction_orchestrator import ExtractionOrchestrator
from app.models.document_upload import DocumentUpload
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
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
    name="app.tasks.extraction_tasks.extract_document",
    bind=True,
    base=DatabaseTask,
    time_limit=600,
    soft_time_limit=540,
    autoretry_for=(ConnectionError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3,
)
def extract_document(self, upload_id: int):
    """
    Celery task: Extract and parse financial document (idempotent).

    Idempotency (P1): Uses Redis lock to prevent duplicate execution. If already
    completed, returns cached success. If lock held by another task, skips.
    """
    task_id = self.request.id
    from app.utils.task_idempotency import acquire_extraction_lock, release_extraction_lock

    # Idempotency: skip if already completed
    db_check = SessionLocal()
    try:
        upload = db_check.query(DocumentUpload).filter(DocumentUpload.id == upload_id).first()
        if upload and upload.extraction_status == "completed":
            logger.info(f"Extraction idempotent skip for upload_id={upload_id} (already completed)")
            return {
                "success": True,
                "upload_id": upload_id,
                "records_inserted": 0,
                "skipped": True,
                "message": "Already completed",
            }
    finally:
        db_check.close()

    # Acquire lock to prevent duplicate concurrent execution
    if not acquire_extraction_lock(upload_id, task_id):
        return {
            "success": True,
            "upload_id": upload_id,
            "skipped": True,
            "message": "Duplicate task skipped",
        }

    try:
        logger.info(f"Starting extraction for upload_id={upload_id}, task_id={task_id}")

        # Update task state to processing
    self.update_state(
        state="PROCESSING",
        meta={
            "upload_id": upload_id,
            "status": "Processing document",
            "progress": 10
        }
    )
    
    try:
        # Get database session
        db = SessionLocal()
        
        # Create orchestrator
        orchestrator = ExtractionOrchestrator(db)
        
        # Update progress - downloading
        self.update_state(
            state="PROCESSING",
            meta={
                "upload_id": upload_id,
                "status": "Downloading from storage",
                "progress": 20
            }
        )
        
        # Execute extraction workflow
        result = orchestrator.extract_and_parse_document(upload_id)
        
        # Close database session
        db.close()
        
        # Update progress based on result
        if result.get("success"):
            logger.info(f"Extraction successful for upload_id={upload_id}")
            self.update_state(
                state="SUCCESS",
                meta={
                    "upload_id": upload_id,
                    "status": "Extraction completed",
                    "progress": 100,
                    "records_inserted": result.get("records_inserted", 0),
                    "confidence_score": result.get("confidence_score", 0),
                    "needs_review": result.get("needs_review", False)
                }
            )
            release_extraction_lock(upload_id, task_id)
            return {
                "success": True,
                "upload_id": upload_id,
                "records_inserted": result.get("records_inserted", 0),
                "confidence_score": result.get("confidence_score", 0),
                "extraction_log_id": result.get("extraction_log_id"),
                "message": "Extraction completed successfully"
            }
        else:
            release_extraction_lock(upload_id, task_id)
            logger.error(f"Extraction failed for upload_id={upload_id}: {result.get('error')}")
            self.update_state(
                state="FAILURE",
                meta={
                    "upload_id": upload_id,
                    "status": "Extraction failed",
                    "progress": 0,
                    "error": result.get("error")
                }
            )
            return {
                "success": False,
                "upload_id": upload_id,
                "error": result.get("error"),
                "message": "Extraction failed"
            }
    except SoftTimeLimitExceeded:
        release_extraction_lock(upload_id, task_id)
        logger.error(f"⏱️  Soft timeout reached for upload_id={upload_id} - gracefully terminating")
        
        # Update database status to failed
        try:
            db = SessionLocal()
            upload = db.query(DocumentUpload).filter(DocumentUpload.id == upload_id).first()
            if upload:
                upload.extraction_status = 'failed'
                upload.notes = "Extraction timeout: Task exceeded 9-minute processing limit"
                db.commit()
                
                # Capture timeout issue for learning
                try:
                    from app.services.issue_capture_service import IssueCaptureService
                    capture_service = IssueCaptureService(db)
                    capture_service.capture_extraction_issue(
                        error=None,
                        error_message="Extraction timeout: Task exceeded 9-minute processing limit",
                        extraction_engine=None,
                        file_size=None,
                        upload_id=upload_id,
                        document_type=upload.document_type,
                        context={
                            "upload_id": upload_id,
                            "timeout_type": "soft_time_limit",
                            "time_limit_seconds": 540
                        }
                    )
                except Exception as capture_error:
                    logger.warning(f"Failed to capture timeout issue: {capture_error}")
            
            db.close()
        except Exception as db_error:
            logger.error(f"Failed to update database after timeout: {db_error}")
        
        self.update_state(
            state="FAILURE",
            meta={
                "upload_id": upload_id,
                "status": "Timeout",
                "progress": 0,
                "error": "Task exceeded time limit (9 minutes)"
            }
        )
        return {
            "success": False,
            "upload_id": upload_id,
            "error": "Task timeout - exceeded processing time limit",
            "message": "Extraction task timed out"
        }
    
    except Exception as e:
        release_extraction_lock(upload_id, task_id)
        logger.exception(f"Exception during extraction for upload_id={upload_id}")
        
        # Update database status to failed
        try:
            db = SessionLocal()
            upload = db.query(DocumentUpload).filter(DocumentUpload.id == upload_id).first()
            if upload:
                upload.extraction_status = 'failed'
                upload.notes = f"Extraction error: {str(e)}"
                db.commit()
                
                # Capture issue for learning
                try:
                    from app.services.issue_capture_service import IssueCaptureService
                    capture_service = IssueCaptureService(db)
                    capture_service.capture_extraction_issue(
                        error=e,
                        error_message=str(e),
                        extraction_engine=None,  # Could extract from context
                        file_size=None,  # Could get from upload
                        upload_id=upload_id,
                        document_type=upload.document_type,
                        context={
                            "upload_id": upload_id,
                            "property_id": upload.property_id,
                            "period_id": upload.period_id
                        }
                    )
                except Exception as capture_error:
                    logger.warning(f"Failed to capture extraction issue: {capture_error}")
            
            db.close()
        except Exception as db_error:
            logger.error(f"Failed to update database after exception: {db_error}")
        
        self.update_state(
            state="FAILURE",
            meta={
                "upload_id": upload_id,
                "status": "Extraction error",
                "progress": 0,
                "error": str(e)
            }
        )
        return {
            "success": False,
            "upload_id": upload_id,
            "error": str(e),
            "message": "Extraction task failed with exception"
        }


@celery_app.task(name="app.tasks.extraction_tasks.retry_failed_extraction")
def retry_failed_extraction(upload_id: int):
    """
    Retry extraction for a failed upload
    
    Args:
        upload_id: DocumentUpload ID
    
    Returns:
        dict: Task info
    """
    logger.info(f"Retrying extraction for upload_id={upload_id}")
    
    # Trigger the main extraction task
    task = extract_document.delay(upload_id)
    
    return {
        "upload_id": upload_id,
        "task_id": task.id,
        "message": "Retry task queued"
    }


@celery_app.task(name="app.tasks.extraction_tasks.recover_stuck_extractions")
def recover_stuck_extractions():
    """
    Find files in uploaded_to_minio or pending status and trigger extraction.
    
    This task runs every minute via Celery Beat to recover files that:
    - Were uploaded to MinIO but extraction wasn't queued (Celery was down)
    - Are stuck in pending status without a task_id
    
    Returns:
        dict: Recovery statistics
    """
    from datetime import datetime, timedelta
    from app.db.database import SessionLocal
    from app.models.document_upload import DocumentUpload
    
    db = SessionLocal()
    recovered_count = 0
    error_count = 0
    
    try:
        # Find files stuck in uploaded_to_minio or pending without task_id
        stuck_uploads = db.query(DocumentUpload).filter(
            DocumentUpload.extraction_status.in_(['uploaded_to_minio', 'pending']),
            DocumentUpload.extraction_task_id.is_(None),  # No task ID means never queued
            DocumentUpload.upload_date > datetime.utcnow() - timedelta(hours=24)  # Only recent files
        ).limit(50).all()
        
        logger.info(f"Recovery task: Found {len(stuck_uploads)} stuck upload(s)")
        
        for upload in stuck_uploads:
            try:
                # Try to queue extraction
                task = extract_document.delay(upload.id)
                upload.extraction_status = 'pending'
                upload.extraction_task_id = task.id
                db.commit()
                recovered_count += 1
                logger.info(f"✅ Recovered upload_id={upload.id}, task_id={task.id}")
            except Exception as e:
                error_count += 1
                logger.error(f"❌ Failed to recover upload_id={upload.id}: {e}")
                # Update notes but don't fail the whole task
                upload.notes = f"Recovery attempt failed: {str(e)}"
                db.commit()
        
        return {
            "recovered": recovered_count,
            "errors": error_count,
            "total_found": len(stuck_uploads)
        }
    except Exception as e:
        logger.error(f"Recovery task failed: {e}")
        return {
            "recovered": recovered_count,
            "errors": error_count,
            "error": str(e)
        }
    finally:
        db.close()


@celery_app.task(name="app.tasks.extraction_tasks.batch_extract_documents")
def batch_extract_documents(upload_ids: list):
    """
    Batch extract multiple documents
    
    Args:
        upload_ids: List of DocumentUpload IDs
    
    Returns:
        dict: Batch processing summary
    """
    logger.info(f"Starting batch extraction for {len(upload_ids)} documents")
    
    results = []
    
    for upload_id in upload_ids:
        # Queue each extraction as a separate task
        task = extract_document.delay(upload_id)
        results.append({
            "upload_id": upload_id,
            "task_id": task.id
        })
    
    return {
        "total_queued": len(upload_ids),
        "tasks": results,
        "message": f"Queued {len(upload_ids)} extraction tasks"
    }


@celery_app.task(name="app.tasks.extraction_tasks.get_extraction_status")
def get_extraction_status(task_id: str):
    """
    Get status of an extraction task
    
    Args:
        task_id: Celery task ID
    
    Returns:
        dict: Task status and metadata
    """
    from celery.result import AsyncResult
    
    task_result = AsyncResult(task_id, app=celery_app)
    
    return {
        "task_id": task_id,
        "state": task_result.state,
        "info": task_result.info if task_result.info else {},
        "ready": task_result.ready(),
        "successful": task_result.successful() if task_result.ready() else None,
        "failed": task_result.failed() if task_result.ready() else None
    }


@celery_app.task(
    name="app.tasks.extraction_tasks.analyze_pdf_async",
    bind=True,
    time_limit=300,  # 5 minutes
)
def analyze_pdf_async(self, file_path: str, bucket_name: str = "reims", strategies: list = None):
    """
    Async task to analyze a PDF without full database ingestion.
    Useful for 'Test Extraction' or temporary analysis.
    """
    from app.utils.extraction_engine import MultiEngineExtractor
    from app.db.minio_client import minio_client

    logger.info(f"Starting async analysis for {file_path}")
    
    self.update_state(state="PROCESSING", meta={"status": "Downloading file"})
    
    try:
        # Download file from MinIO
        response = minio_client.get_object(bucket_name, file_path)
        pdf_data = response.read()
        response.close()
        response.release_conn()
        
        # Initialize extractor
        extractor = MultiEngineExtractor()
        
        self.update_state(state="PROCESSING", meta={"status": "Extracting content"})
        
        # Extract
        # Note: We rely on default strategies if not provided
        result = extractor.extract_with_validation(pdf_data)
        
        return result
        
    except Exception as e:
        logger.error(f"Async analysis failed: {e}")
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise e

