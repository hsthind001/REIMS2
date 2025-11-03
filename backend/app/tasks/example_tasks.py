import time
from celery import shared_task
from app.core.celery_config import celery_app


@celery_app.task(name="app.tasks.example_tasks.send_email")
def send_email(email: str, subject: str, body: str):
    """
    Example task: Send an email (simulated)
    """
    # Simulate email sending delay
    time.sleep(3)
    
    result = {
        "status": "sent",
        "email": email,
        "subject": subject,
        "message": f"Email sent to {email} with subject: {subject}"
    }
    
    print(f"Email sent to {email}")
    return result


@celery_app.task(name="app.tasks.example_tasks.process_data")
def process_data(data: dict):
    """
    Example task: Process data asynchronously
    """
    # Simulate data processing
    time.sleep(5)
    
    processed_data = {
        "original": data,
        "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "completed"
    }
    
    print(f"Data processed: {data}")
    return processed_data


@celery_app.task(name="app.tasks.example_tasks.long_running_task")
def long_running_task(duration: int = 10):
    """
    Example task: Long running task with progress tracking
    """
    for i in range(duration):
        time.sleep(1)
        # Update task state
        long_running_task.update_state(
            state="PROGRESS",
            meta={"current": i + 1, "total": duration, "status": f"Processing step {i + 1}/{duration}"}
        )
    
    return {
        "status": "completed",
        "duration": duration,
        "message": f"Task completed after {duration} seconds"
    }


@celery_app.task(name="app.tasks.example_tasks.add_numbers", bind=True)
def add_numbers(self, x: int, y: int):
    """
    Example task: Simple mathematical operation
    """
    result = x + y
    return {
        "task_id": self.request.id,
        "x": x,
        "y": y,
        "result": result
    }

