from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from app.tasks.example_tasks import send_email, process_data, long_running_task, add_numbers
from celery.result import AsyncResult
from app.core.celery_config import celery_app

router = APIRouter()


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

