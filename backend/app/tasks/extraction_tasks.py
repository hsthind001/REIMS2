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
    time_limit=600,  # 10 minutes hard limit
    soft_time_limit=540  # 9 minutes soft limit (allows graceful cleanup)
)
def extract_document(self, upload_id: int):
    """
    Celery task: Extract and parse financial document
    
    This task is triggered after document upload and runs asynchronously.
    It downloads the PDF from MinIO, extracts the content, parses financial
    data, and inserts into the appropriate tables.
    
    Timeout: 10 minutes (hard), 9 minutes (soft warning)
    
    Args:
        upload_id: DocumentUpload ID
    
    Returns:
        dict: Extraction result with status and details
    """
    logger.info(f"Starting extraction for upload_id={upload_id}, task_id={self.request.id}")
    
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
            return {
                "success": True,
                "upload_id": upload_id,
                "records_inserted": result.get("records_inserted", 0),
                "confidence_score": result.get("confidence_score", 0),
                "extraction_log_id": result.get("extraction_log_id"),
                "message": "Extraction completed successfully"
            }
        else:
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
        logger.error(f"⏱️  Soft timeout reached for upload_id={upload_id} - gracefully terminating")
        
        # Update database status to failed
        try:
            db = SessionLocal()
            upload = db.query(DocumentUpload).filter(DocumentUpload.id == upload_id).first()
            if upload:
                upload.extraction_status = 'failed'
                upload.notes = "Extraction timeout: Task exceeded 9-minute processing limit"
                db.commit()
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
        logger.exception(f"Exception during extraction for upload_id={upload_id}")
        
        # Update database status to failed
        try:
            db = SessionLocal()
            upload = db.query(DocumentUpload).filter(DocumentUpload.id == upload_id).first()
            if upload:
                upload.extraction_status = 'failed'
                upload.notes = f"Extraction error: {str(e)}"
                db.commit()
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

