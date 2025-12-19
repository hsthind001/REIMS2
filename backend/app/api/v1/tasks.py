from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func
from app.tasks.example_tasks import send_email, process_data, long_running_task, add_numbers
from celery.result import AsyncResult
from app.core.celery_config import celery_app
from app.db.database import get_db
from app.models.document_upload import DocumentUpload
from app.models.property import Property
from app.models.financial_period import FinancialPeriod

router = APIRouter()


# Helper functions
def format_task_time(time_value: Any) -> Optional[str]:
    """
    Safely format task time to ISO string.
    Handles Unix timestamps, datetime objects, and ISO strings.

    Returns None if unable to parse.
    """
    if not time_value:
        return None

    try:
        # Handle Unix timestamp (float or int)
        if isinstance(time_value, (int, float)):
            dt = datetime.fromtimestamp(time_value)
            return dt.isoformat()

        # Handle datetime object
        if isinstance(time_value, datetime):
            return time_value.isoformat()

        # Handle string (already formatted or ISO string)
        if isinstance(time_value, str):
            # Try to parse and re-format to ensure consistency
            try:
                # Remove 'Z' and parse
                clean_str = str(time_value).replace('Z', '+00:00')
                dt = datetime.fromisoformat(clean_str)
                return dt.isoformat()
            except (ValueError, AttributeError):
                # If parsing fails, return as-is if it looks like an ISO string
                if 'T' in str(time_value) or '-' in str(time_value):
                    return str(time_value)
                return None

        return None
    except Exception as e:
        # Log error but don't crash
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to format task time {time_value}: {e}")
        return None


# Request models
class EmailTask(BaseModel):
    email: str
    subject: str
    body: str


class DataProcessTask(BaseModel):
    data: dict


class AddNumbersTask(BaseModel):
    x: int
    y: int


class LongRunningTaskRequest(BaseModel):
    duration: int = 10


# Response models
class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


@router.post("/tasks/send-email", response_model=TaskResponse)
async def create_send_email_task(task: EmailTask):
    """
    Create an async task to send an email
    """
    result = send_email.delay(task.email, task.subject, task.body)
    
    return {
        "task_id": result.id,
        "status": "queued",
        "message": f"Email task created for {task.email}"
    }


@router.post("/tasks/process-data", response_model=TaskResponse)
async def create_process_data_task(task: DataProcessTask):
    """
    Create an async task to process data
    """
    result = process_data.delay(task.data)
    
    return {
        "task_id": result.id,
        "status": "queued",
        "message": "Data processing task created"
    }


@router.post("/tasks/add-numbers", response_model=TaskResponse)
async def create_add_numbers_task(task: AddNumbersTask):
    """
    Create an async task to add two numbers
    """
    result = add_numbers.delay(task.x, task.y)
    
    return {
        "task_id": result.id,
        "status": "queued",
        "message": f"Addition task created: {task.x} + {task.y}"
    }


@router.post("/tasks/long-running", response_model=TaskResponse)
async def create_long_running_task(task: LongRunningTaskRequest):
    """
    Create a long-running task with progress tracking
    """
    result = long_running_task.delay(task.duration)
    
    return {
        "task_id": result.id,
        "status": "queued",
        "message": f"Long running task created (duration: {task.duration}s)"
    }


@router.get("/tasks")
async def list_active_tasks():
    """
    List all active tasks (requires Celery events enabled)
    """
    # Get active tasks from all workers
    inspect = celery_app.control.inspect()
    active_tasks = inspect.active()
    scheduled_tasks = inspect.scheduled()
    reserved_tasks = inspect.reserved()
    
    return {
        "active": active_tasks or {},
        "scheduled": scheduled_tasks or {},
        "reserved": reserved_tasks or {}
    }


def parse_task_type(task_name: str) -> str:
    """Parse task name to determine task type"""
    if 'extract_document' in task_name or 'extraction' in task_name:
        return 'document_extraction'
    elif 'anomaly' in task_name:
        return 'anomaly_detection'
    elif 'retry' in task_name or 'recover' in task_name:
        return 'recovery'
    elif 'email' in task_name:
        return 'email'
    elif 'batch' in task_name:
        return 'batch_processing'
    else:
        return 'other'


def extract_upload_id_from_task(task_info: Dict) -> Optional[int]:
    """Extract upload_id from task arguments or metadata"""
    try:
        # Check args (for extract_document tasks)
        if 'args' in task_info and task_info['args']:
            args = task_info['args']
            if isinstance(args, (list, tuple)) and len(args) > 0:
                # First argument is usually upload_id for extraction tasks
                if isinstance(args[0], int):
                    return args[0]
        
        # Check kwargs
        if 'kwargs' in task_info and task_info['kwargs']:
            kwargs = task_info['kwargs']
            if 'upload_id' in kwargs:
                return kwargs['upload_id']
        
        # Check task metadata/result
        if 'result' in task_info:
            result = task_info['result']
            if isinstance(result, dict) and 'upload_id' in result:
                return result['upload_id']
    except Exception:
        pass
    return None


# IMPORTANT: This route must come BEFORE /tasks/{task_id} to avoid route conflicts
@router.get("/tasks/dashboard")
async def get_task_dashboard(db: Session = Depends(get_db)):
    """
    Get comprehensive task dashboard data including:
    - Active tasks with progress and metadata
    - Queue statistics
    - Worker status
    - Recent task history
    - Task statistics
    """
    try:
        inspect = celery_app.control.inspect()
        
        # Get active, scheduled, and reserved tasks
        active_tasks_raw = inspect.active() or {}
        scheduled_tasks_raw = inspect.scheduled() or {}
        reserved_tasks_raw = inspect.reserved() or {}
        
        # Get worker stats
        worker_stats = inspect.stats() or {}
        
        # Parse active tasks
        active_tasks = []
        all_task_ids = set()
        
        # Process active tasks
        for worker_id, tasks in active_tasks_raw.items():
            for task in tasks:
                task_id = task.get('id')
                task_name = task.get('name', '')
                all_task_ids.add(task_id)
                
                # Get task result for progress
                task_result = AsyncResult(task_id, app=celery_app)
                task_state = task_result.state
                task_meta = {}
                
                if task_state == 'PROGRESS' and task_result.info:
                    task_meta = task_result.info if isinstance(task_result.info, dict) else {}
                
                # Extract upload_id
                upload_id = extract_upload_id_from_task(task)
                if not upload_id:
                    # Try to get from task args
                    upload_id = extract_upload_id_from_task({'args': task.get('args', [])})
                
                # Get document info if upload_id exists
                document_name = None
                property_code = None
                if upload_id:
                    upload = db.query(DocumentUpload).filter(
                        DocumentUpload.id == upload_id
                    ).first()
                    if upload:
                        document_name = upload.file_name
                        # Get property code
                        prop = db.query(Property).filter(Property.id == upload.property_id).first()
                        if prop:
                            property_code = prop.property_code
                
                # Parse task type
                task_type = parse_task_type(task_name)
                
                # Extract progress
                progress = task_meta.get('progress', 0) if task_meta else 0
                current_step = task_meta.get('status', task_state) if task_meta else task_state
                
                # Calculate ETA (rough estimate based on progress)
                eta_seconds = None
                if progress > 0 and progress < 100:
                    # Estimate: if 50% done in X seconds, remaining is X seconds
                    # This is a rough estimate - could be improved with actual timing
                    time_start = task.get('time_start')
                    if time_start:
                        try:
                            if isinstance(time_start, (int, float)):
                                # Unix timestamp
                                time_start_dt = datetime.fromtimestamp(time_start)
                            else:
                                # ISO string or datetime
                                time_start_dt = time_start if isinstance(time_start, datetime) else datetime.fromisoformat(str(time_start).replace('Z', '+00:00'))
                            elapsed = (datetime.utcnow() - time_start_dt).total_seconds()
                            if elapsed > 0:
                                estimated_total = elapsed / (progress / 100.0)
                                eta_seconds = int(estimated_total - elapsed)
                        except Exception:
                            pass  # Skip ETA calculation if time parsing fails
                
                active_tasks.append({
                    "task_id": task_id,
                    "task_name": task_name,
                    "task_type": task_type,
                    "status": task_state,
                    "progress": progress,
                    "current_step": current_step,
                    "upload_id": upload_id,
                    "document_name": document_name,
                    "property_code": property_code,
                    "started_at": format_task_time(task.get('time_start')),
                    "eta_seconds": eta_seconds,
                    "worker_id": worker_id
                })
        
        # Count queue stats
        pending_count = sum(len(tasks) for tasks in scheduled_tasks_raw.values())
        processing_count = len(active_tasks)
        reserved_count = sum(len(tasks) for tasks in reserved_tasks_raw.values())
        
        # Get today's task statistics from database
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Count completed extractions today
        completed_today = db.query(DocumentUpload).filter(
            DocumentUpload.extraction_completed_at >= today_start,
            DocumentUpload.extraction_status == 'completed'
        ).count()
        
        # Count failed extractions today
        failed_today = db.query(DocumentUpload).filter(
            DocumentUpload.extraction_completed_at >= today_start,
            DocumentUpload.extraction_status == 'failed'
        ).count()
        
        # Calculate success rate
        total_today = completed_today + failed_today
        success_rate = (completed_today / total_today * 100) if total_today > 0 else 100.0
        
        # Get recent tasks (last 50 completed extractions)
        recent_uploads = db.query(DocumentUpload).filter(
            DocumentUpload.extraction_completed_at.isnot(None),
            DocumentUpload.extraction_task_id.isnot(None)
        ).order_by(DocumentUpload.extraction_completed_at.desc()).limit(20).all()
        
        recent_tasks = []
        for upload in recent_uploads:
            if upload.extraction_task_id:
                task_result = AsyncResult(upload.extraction_task_id, app=celery_app)
                duration_seconds = None
                if upload.extraction_started_at and upload.extraction_completed_at:
                    duration_seconds = int((upload.extraction_completed_at - upload.extraction_started_at).total_seconds())
                
                recent_tasks.append({
                    "task_id": upload.extraction_task_id,
                    "task_name": "extract_document",
                    "task_type": "document_extraction",
                    "status": "SUCCESS" if upload.extraction_status == 'completed' else "FAILURE",
                    "duration_seconds": duration_seconds,
                    "upload_id": upload.id,
                    "document_name": upload.file_name,
                    "completed_at": upload.extraction_completed_at.isoformat() if upload.extraction_completed_at else None
                })
        
        # Get worker information
        workers = []
        for worker_id, stats in worker_stats.items():
            # Get active task count for this worker
            worker_active_tasks = active_tasks_raw.get(worker_id, [])
            active_count = len(worker_active_tasks)
            
            workers.append({
                "worker_id": worker_id,
                "status": "online",
                "active_tasks": active_count,
                "cpu_percent": stats.get('pool', {}).get('processes', {}).get('cpu', 0) if isinstance(stats.get('pool'), dict) else 0,
                "memory_mb": 0  # Celery stats don't always include memory
            })
        
        # Calculate task statistics
        # Average extraction time (from recent completed tasks)
        avg_extraction_time = 0
        extraction_times = [t['duration_seconds'] for t in recent_tasks if t.get('duration_seconds')]
        if extraction_times:
            avg_extraction_time = sum(extraction_times) / len(extraction_times)
        
        # Count by type
        by_type = {}
        for task in active_tasks + recent_tasks:
            task_type = task.get('task_type', 'other')
            if task_type not in by_type:
                by_type[task_type] = {"count": 0, "avg_time": 0}
            by_type[task_type]["count"] += 1
            if task.get('duration_seconds'):
                current_avg = by_type[task_type]["avg_time"]
                count = by_type[task_type]["count"]
                by_type[task_type]["avg_time"] = ((current_avg * (count - 1)) + task['duration_seconds']) / count
        
        return {
            "active_tasks": active_tasks,
            "queue_stats": {
                "pending": pending_count + reserved_count,
                "processing": processing_count,
                "completed_today": completed_today,
                "failed_today": failed_today,
                "success_rate": round(success_rate, 2)
            },
            "workers": workers,
            "recent_tasks": recent_tasks[:20],  # Limit to 20
            "task_statistics": {
                "avg_extraction_time": round(avg_extraction_time, 2),
                "total_tasks_today": total_today,
                "by_type": by_type
            }
        }
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get task dashboard: {str(e)}", exc_info=True)
        
        # Return safe defaults if Celery is unavailable
        return {
            "active_tasks": [],
            "queue_stats": {
                "pending": 0,
                "processing": 0,
                "completed_today": 0,
                "failed_today": 0,
                "success_rate": 0.0
            },
            "workers": [],
            "recent_tasks": [],
            "task_statistics": {
                "avg_extraction_time": 0,
                "total_tasks_today": 0,
                "by_type": {}
            },
            "error": "Celery unavailable or error occurred"
        }


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    Get the status of a task by ID
    """
    task_result = AsyncResult(task_id, app=celery_app)
    
    response = {
        "task_id": task_id,
        "status": task_result.status,
        "ready": task_result.ready(),
        "successful": task_result.successful() if task_result.ready() else None,
    }
    
    if task_result.ready():
        if task_result.successful():
            response["result"] = task_result.result
        else:
            response["error"] = str(task_result.info)
    elif task_result.state == "PROGRESS":
        response["progress"] = task_result.info
    
    return response


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """
    Cancel a running task
    """
    task_result = AsyncResult(task_id, app=celery_app)
    
    if not task_result.ready():
        task_result.revoke(terminate=True)
        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": "Task has been cancelled"
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task has already completed"
        )


# Phase 2: Extended History Endpoint
@router.get("/tasks/history")
async def get_task_history(
    days: int = 7,
    db: Session = Depends(get_db)
):
    """
    Get extended task history for the last N days
    """
    try:
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get all completed extractions from the last N days
        recent_uploads = db.query(DocumentUpload).filter(
            DocumentUpload.extraction_completed_at.isnot(None),
            DocumentUpload.extraction_completed_at >= cutoff_date,
            DocumentUpload.extraction_task_id.isnot(None)
        ).order_by(DocumentUpload.extraction_completed_at.desc()).all()
        
        history = []
        for upload in recent_uploads:
            if upload.extraction_task_id:
                task_result = AsyncResult(upload.extraction_task_id, app=celery_app)
                duration_seconds = None
                if upload.extraction_started_at and upload.extraction_completed_at:
                    duration_seconds = int((upload.extraction_completed_at - upload.extraction_started_at).total_seconds())
                
                # Get property code
                property_code = None
                if upload.property_id:
                    prop = db.query(Property).filter(Property.id == upload.property_id).first()
                    if prop:
                        property_code = prop.property_code
                
                history.append({
                    "task_id": upload.extraction_task_id,
                    "task_name": "extract_document",
                    "task_type": "document_extraction",
                    "status": "SUCCESS" if upload.extraction_status == 'completed' else "FAILURE",
                    "duration_seconds": duration_seconds,
                    "upload_id": upload.id,
                    "document_name": upload.file_name,
                    "property_code": property_code,
                    "completed_at": upload.extraction_completed_at.isoformat() if upload.extraction_completed_at else None,
                    "started_at": upload.extraction_started_at.isoformat() if upload.extraction_started_at else None
                })
        
        return history
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get task history: {str(e)}", exc_info=True)
        return []


# Phase 2: Bulk Cancel Endpoint
class BulkCancelRequest(BaseModel):
    task_ids: List[str]

@router.post("/tasks/bulk/cancel")
async def bulk_cancel_tasks(
    request: BulkCancelRequest,
    db: Session = Depends(get_db)
):
    """
    Cancel multiple tasks at once
    """
    cancelled = 0
    failed = 0
    errors = []
    
    for task_id in request.task_ids:
        try:
            task_result = AsyncResult(task_id, app=celery_app)
            if not task_result.ready():
                task_result.revoke(terminate=True)
                cancelled += 1
            else:
                failed += 1
                errors.append(f"Task {task_id} already completed")
        except Exception as e:
            failed += 1
            errors.append(f"Task {task_id}: {str(e)}")
    
    return {
        "cancelled": cancelled,
        "failed": failed,
        "errors": errors[:10]  # Limit to first 10 errors
    }

