from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func
from app.tasks.example_tasks import send_email, process_data, long_running_task, add_numbers
from celery.result import AsyncResult
from celery.schedules import crontab
from app.core.celery_config import celery_app
from app.db.database import get_db
from app.api.dependencies import get_current_user, get_current_user_hybrid, get_current_organization
from app.models.user import User
from app.models.organization import Organization
from app.repositories.tenant_scoped import get_upload_for_org
from app.models.document_upload import DocumentUpload
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.scheduled_task import ScheduledTask, ScheduleType, TaskStatus
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


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


def _require_dev_or_auth() -> None:
    """E1-S2: Demo tasks restricted to dev; disabled in production."""
    from app.core.config import settings
    env = (settings.ENVIRONMENT or "development").lower()
    if env == "production":
        raise HTTPException(status_code=404, detail="Demo task endpoints disabled in production")


@router.post("/tasks/send-email", response_model=TaskResponse)
async def create_send_email_task(
    task: EmailTask,
    current_user: User = Depends(get_current_user_hybrid),
):
    """Create an async task to send an email. E1-S2: Auth required; disabled in production."""
    _require_dev_or_auth()
    result = send_email.delay(task.email, task.subject, task.body)
    
    return {
        "task_id": result.id,
        "status": "queued",
        "message": f"Email task created for {task.email}"
    }


@router.post("/tasks/process-data", response_model=TaskResponse)
async def create_process_data_task(
    task: DataProcessTask,
    current_user: User = Depends(get_current_user_hybrid),
):
    """Create an async task to process data. E1-S2: Auth required; disabled in production."""
    _require_dev_or_auth()
    result = process_data.delay(task.data)
    
    return {
        "task_id": result.id,
        "status": "queued",
        "message": "Data processing task created"
    }


@router.post("/tasks/add-numbers", response_model=TaskResponse)
async def create_add_numbers_task(
    task: AddNumbersTask,
    current_user: User = Depends(get_current_user_hybrid),
):
    """Create an async task to add two numbers. E1-S2: Auth required; disabled in production."""
    _require_dev_or_auth()
    result = add_numbers.delay(task.x, task.y)
    
    return {
        "task_id": result.id,
        "status": "queued",
        "message": f"Addition task created: {task.x} + {task.y}"
    }


@router.post("/tasks/long-running", response_model=TaskResponse)
async def create_long_running_task(
    task: LongRunningTaskRequest,
    current_user: User = Depends(get_current_user_hybrid),
):
    """Create a long-running task with progress tracking. E1-S2: Auth required; disabled in production."""
    _require_dev_or_auth()
    result = long_running_task.delay(task.duration)
    
    return {
        "task_id": result.id,
        "status": "queued",
        "message": f"Long running task created (duration: {task.duration}s)"
    }


@router.get("/tasks")
async def list_active_tasks(
    current_user: User = Depends(get_current_user_hybrid),
):
    """List all active tasks (requires Celery events enabled). E1-S2: Auth required."""
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
async def get_task_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
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
                
                # Get document info if upload_id exists (tenant-scoped)
                # Skip tasks for uploads not belonging to this org
                document_name = None
                property_code = None
                if upload_id:
                    upload = get_upload_for_org(db, current_org.id, upload_id)
                    if not upload:
                        continue  # Exclude tasks for other orgs' uploads
                    document_name = upload.file_name
                    property_code = upload.property.property_code if upload.property else None

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
        
        # Get today's task statistics from database (tenant-scoped)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        completed_today = (
            db.query(DocumentUpload)
            .join(Property, DocumentUpload.property_id == Property.id)
            .filter(
                DocumentUpload.extraction_completed_at >= today_start,
                DocumentUpload.extraction_status == 'completed',
                Property.organization_id == current_org.id,
            )
            .count()
        )
        failed_today = (
            db.query(DocumentUpload)
            .join(Property, DocumentUpload.property_id == Property.id)
            .filter(
                DocumentUpload.extraction_completed_at >= today_start,
                DocumentUpload.extraction_status == 'failed',
                Property.organization_id == current_org.id,
            )
            .count()
        )
        
        # Calculate success rate
        total_today = completed_today + failed_today
        success_rate = (completed_today / total_today * 100) if total_today > 0 else 100.0
        
        # Get recent tasks (tenant-scoped)
        recent_uploads = (
            db.query(DocumentUpload)
            .join(Property, DocumentUpload.property_id == Property.id)
            .filter(
                DocumentUpload.extraction_completed_at.isnot(None),
                DocumentUpload.extraction_task_id.isnot(None),
                Property.organization_id == current_org.id,
            )
            .order_by(DocumentUpload.extraction_completed_at.desc())
            .limit(20)
            .all()
        )
        
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

            # Handle both dict and list stats formats
            cpu_percent = 0
            if isinstance(stats, dict):
                pool_data = stats.get('pool', {})
                if isinstance(pool_data, dict):
                    processes = pool_data.get('processes', {})
                    if isinstance(processes, dict):
                        cpu_percent = processes.get('cpu', 0)

            workers.append({
                "worker_id": worker_id,
                "status": "online",
                "active_tasks": active_count,
                "cpu_percent": cpu_percent,
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
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user_hybrid),
):
    """Get the status of a task by ID. E1-S2: Auth required."""
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
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user_hybrid),
):
    """Cancel a running task. E1-S2: Auth required."""
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """Get extended task history for the last N days. Tenant-scoped."""
    try:
        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_uploads = (
            db.query(DocumentUpload)
            .join(Property, DocumentUpload.property_id == Property.id)
            .filter(
                DocumentUpload.extraction_completed_at.isnot(None),
                DocumentUpload.extraction_completed_at >= cutoff_date,
                DocumentUpload.extraction_task_id.isnot(None),
                Property.organization_id == current_org.id,
            )
            .order_by(DocumentUpload.extraction_completed_at.desc())
            .all()
        )
        
        history = []
        for upload in recent_uploads:
            if upload.extraction_task_id:
                task_result = AsyncResult(upload.extraction_task_id, app=celery_app)
                duration_seconds = None
                if upload.extraction_started_at and upload.extraction_completed_at:
                    duration_seconds = int((upload.extraction_completed_at - upload.extraction_started_at).total_seconds())
                
                property_code = upload.property.property_code if upload.property else None
                
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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


# ===== Scheduled Tasks API =====

class CreateScheduledTaskRequest(BaseModel):
    task_type: str
    schedule_type: str  # 'once' or 'recurring'
    scheduled_time: Optional[datetime] = None  # For 'once' type
    cron_expression: Optional[str] = None  # For 'recurring' type
    parameters: Optional[Dict[str, Any]] = None
    task_name: Optional[str] = None
    notes: Optional[str] = None


class ScheduledTaskResponse(BaseModel):
    id: int
    task_type: str
    schedule_type: str
    task_name: Optional[str]
    scheduled_time: Optional[datetime]
    cron_expression: Optional[str]
    parameters: Optional[Dict[str, Any]]
    status: str
    next_run_at: Optional[datetime]
    run_count: int
    failure_count: int
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


@router.post("/tasks/scheduled", response_model=ScheduledTaskResponse)
async def create_scheduled_task(
    request: CreateScheduledTaskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a scheduled task for future execution or recurring schedule
    """
    try:
        # Validate schedule type
        if request.schedule_type == 'once':
            if not request.scheduled_time:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="scheduled_time is required for 'once' schedule type"
                )
            if request.scheduled_time < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="scheduled_time must be in the future"
                )
        elif request.schedule_type == 'recurring':
            if not request.cron_expression:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="cron_expression is required for 'recurring' schedule type"
                )
            # Validate cron expression format (basic check)
            parts = request.cron_expression.split()
            if len(parts) != 5:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid cron expression format. Expected: 'minute hour day month weekday'"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="schedule_type must be 'once' or 'recurring'"
            )
        
        # Create scheduled task record
        scheduled_task = ScheduledTask(
            task_type=request.task_type,
            schedule_type=ScheduleType(request.schedule_type),
            task_name=request.task_name or f"{request.task_type} - {request.schedule_type}",
            scheduled_time=request.scheduled_time,
            cron_expression=request.cron_expression,
            parameters=json.dumps(request.parameters) if request.parameters else None,
            status=TaskStatus.PENDING,
            created_by=current_user.id,
            notes=request.notes,
            is_active=True
        )
        
        # Calculate next_run_at
        if request.schedule_type == 'once':
            scheduled_task.next_run_at = request.scheduled_time
        else:
            # For recurring, next run would be calculated by Celery Beat
            # For now, set to None - will be updated when Beat picks it up
            scheduled_task.next_run_at = None
        
        db.add(scheduled_task)
        db.commit()
        db.refresh(scheduled_task)
        
        # Schedule with Celery
        if request.schedule_type == 'once':
            # Use apply_async with eta for one-time tasks
            try:
                task_func = _get_task_function(request.task_type)
                if task_func:
                    task_params = request.parameters or {}
                    result = task_func.apply_async(
                        args=[],
                        kwargs=task_params,
                        eta=request.scheduled_time
                    )
                    logger.info(f"Scheduled one-time task {scheduled_task.id} with Celery task ID: {result.id}")
            except Exception as e:
                logger.warning(f"Failed to schedule Celery task for scheduled_task {scheduled_task.id}: {str(e)}")
        else:
            # Add to Celery Beat schedule for recurring tasks
            try:
                schedule_id = f"scheduled_task_{scheduled_task.id}"
                cron_parts = request.cron_expression.split()
                
                celery_app.conf.beat_schedule[schedule_id] = {
                    'task': _get_task_name(request.task_type),
                    'schedule': crontab(
                        minute=cron_parts[0],
                        hour=cron_parts[1],
                        day_of_month=cron_parts[2],
                        month_of_year=cron_parts[3],
                        day_of_week=cron_parts[4]
                    ),
                    'args': [],
                    'kwargs': request.parameters or {}
                }
                scheduled_task.celery_beat_schedule_id = schedule_id
                db.commit()
                logger.info(f"Added recurring task {scheduled_task.id} to Celery Beat schedule: {schedule_id}")
            except Exception as e:
                logger.warning(f"Failed to add task to Celery Beat schedule: {str(e)}")
        
        return ScheduledTaskResponse(
            id=scheduled_task.id,
            task_type=scheduled_task.task_type,
            schedule_type=scheduled_task.schedule_type.value,
            task_name=scheduled_task.task_name,
            scheduled_time=scheduled_task.scheduled_time,
            cron_expression=scheduled_task.cron_expression,
            parameters=json.loads(scheduled_task.parameters) if scheduled_task.parameters else None,
            status=scheduled_task.status.value,
            next_run_at=scheduled_task.next_run_at,
            run_count=scheduled_task.run_count,
            failure_count=scheduled_task.failure_count,
            created_at=scheduled_task.created_at,
            is_active=scheduled_task.is_active
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create scheduled task: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create scheduled task: {str(e)}"
        )


@router.get("/tasks/scheduled", response_model=List[ScheduledTaskResponse])
async def list_scheduled_tasks(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    List all scheduled tasks, optionally filtered by active status
    """
    try:
        query = db.query(ScheduledTask)
        if is_active is not None:
            query = query.filter(ScheduledTask.is_active == is_active)
        
        tasks = query.order_by(ScheduledTask.created_at.desc()).all()
        
        return [
            ScheduledTaskResponse(
                id=task.id,
                task_type=task.task_type,
                schedule_type=task.schedule_type.value,
                task_name=task.task_name,
                scheduled_time=task.scheduled_time,
                cron_expression=task.cron_expression,
                parameters=json.loads(task.parameters) if task.parameters else None,
                status=task.status.value,
                next_run_at=task.next_run_at,
                run_count=task.run_count,
                failure_count=task.failure_count,
                created_at=task.created_at,
                is_active=task.is_active
            )
            for task in tasks
        ]
    except Exception as e:
        logger.error(f"Failed to list scheduled tasks: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list scheduled tasks: {str(e)}"
        )


@router.delete("/tasks/scheduled/{task_id}")
async def delete_scheduled_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a scheduled task and remove it from Celery Beat if recurring
    """
    try:
        task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scheduled task {task_id} not found"
            )
        
        # Remove from Celery Beat if it's a recurring task
        if task.schedule_type == ScheduleType.RECURRING and task.celery_beat_schedule_id:
            try:
                if task.celery_beat_schedule_id in celery_app.conf.beat_schedule:
                    del celery_app.conf.beat_schedule[task.celery_beat_schedule_id]
                    logger.info(f"Removed recurring task {task_id} from Celery Beat schedule")
            except Exception as e:
                logger.warning(f"Failed to remove task from Celery Beat: {str(e)}")
        
        # Mark as inactive instead of deleting (for audit trail)
        task.is_active = False
        task.status = TaskStatus.CANCELLED
        db.commit()
        
        return {
            "success": True,
            "message": f"Scheduled task {task_id} deleted successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete scheduled task: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete scheduled task: {str(e)}"
        )


def _get_task_function(task_type: str):
    """Get Celery task function by task type"""
    task_map = {
        'extract_document': None,  # Would need to import from extraction_tasks
        'anomaly_detection': None,  # Would need to import from anomaly_detection_tasks
        'recover_stuck_extractions': None,  # Would need to import
    }
    return task_map.get(task_type)


def _get_task_name(task_type: str) -> str:
    """Get Celery task name by task type"""
    task_name_map = {
        'extract_document': 'app.tasks.extraction_tasks.extract_document',
        'anomaly_detection': 'app.tasks.anomaly_detection_tasks.run_nightly_anomaly_detection',
        'recover_stuck_extractions': 'app.tasks.extraction_tasks.recover_stuck_extractions',
    }
    return task_name_map.get(task_type, f'app.tasks.{task_type}')

