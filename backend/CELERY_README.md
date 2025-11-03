# Celery - Distributed Task Queue

Celery is configured for asynchronous task processing using Redis as the broker and result backend.

## What is Celery?

Celery allows you to run time-consuming tasks asynchronously in the background:
- Send emails
- Process large datasets
- Generate reports
- Image/video processing
- Scheduled tasks (with Celery Beat)

## Starting Celery Worker

### Development Mode

```bash
cd /home/gurpyar/Documents/R/REIMS2/backend
source venv/bin/activate

# Start Celery worker
celery -A celery_worker.celery_app worker --loglevel=info
```

### Production Mode (Detached)

```bash
# Start worker in background
celery -A celery_worker.celery_app worker --loglevel=info --detach \
  --pidfile=/tmp/celery_worker.pid \
  --logfile=/tmp/celery_worker.log

# Stop worker
pkill -f "celery worker"

# Or use the PID file
kill $(cat /tmp/celery_worker.pid)
```

### With Specific Queues

```bash
# Listen to specific queues
celery -A celery_worker.celery_app worker --loglevel=info -Q default,email
```

## Monitoring with Flower

Flower is a web-based tool for monitoring Celery workers and tasks.

### Start Flower

```bash
cd /home/gurpyar/Documents/R/REIMS2/backend
source venv/bin/activate

celery -A celery_worker.celery_app flower --port=5555
```

Access Flower at: http://localhost:5555

## Available Tasks

### 1. Send Email Task
```python
POST /api/v1/tasks/send-email
{
    "email": "user@example.com",
    "subject": "Test Email",
    "body": "This is a test email"
}
```

### 2. Process Data Task
```python
POST /api/v1/tasks/process-data
{
    "data": {"key": "value", "numbers": [1, 2, 3]}
}
```

### 3. Add Numbers Task
```python
POST /api/v1/tasks/add-numbers
{
    "x": 10,
    "y": 20
}
```

### 4. Long Running Task
```python
POST /api/v1/tasks/long-running
{
    "duration": 15
}
```

## Check Task Status

```bash
GET /api/v1/tasks/{task_id}
```

Response:
```json
{
    "task_id": "abc-123-def",
    "status": "SUCCESS",
    "ready": true,
    "successful": true,
    "result": {"x": 10, "y": 20, "result": 30}
}
```

## Cancel Task

```bash
DELETE /api/v1/tasks/{task_id}
```

## List Active Tasks

```bash
GET /api/v1/tasks
```

## Creating New Tasks

1. **Create task function** in `app/tasks/`:

```python
from app.core.celery_config import celery_app

@celery_app.task(name="app.tasks.my_task")
def my_custom_task(param1, param2):
    # Your task logic here
    result = param1 + param2
    return {"result": result}
```

2. **Add to celery_config.py** include list:

```python
celery_app = Celery(
    "reims",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.example_tasks", "app.tasks.my_tasks"]  # Add here
)
```

3. **Create API endpoint** in `app/api/v1/`:

```python
from app.tasks.my_tasks import my_custom_task

@router.post("/tasks/my-task")
async def create_my_task(data: MyTaskModel):
    result = my_custom_task.delay(data.param1, data.param2)
    return {"task_id": result.id, "status": "queued"}
```

## Task Options

### Retry on Failure

```python
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def my_task(self, param):
    try:
        # Task logic
        pass
    except Exception as exc:
        raise self.retry(exc=exc)
```

### Task with Timeout

```python
@celery_app.task(time_limit=300, soft_time_limit=280)  # 5 minutes hard, 4:40 soft
def long_task():
    # Task logic
    pass
```

### Progress Tracking

```python
@celery_app.task(bind=True)
def progress_task(self, total):
    for i in range(total):
        self.update_state(
            state='PROGRESS',
            meta={'current': i, 'total': total}
        )
        # Do work
    return {'status': 'completed'}
```

## Scheduled Tasks (Celery Beat)

To run periodic tasks, you need Celery Beat.

### Install Beat

```bash
# Already included with celery
```

### Configure Periodic Tasks

Add to `app/core/celery_config.py`:

```python
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'send-daily-report': {
        'task': 'app.tasks.example_tasks.generate_report',
        'schedule': crontab(hour=9, minute=0),  # 9:00 AM daily
    },
    'cleanup-every-hour': {
        'task': 'app.tasks.cleanup',
        'schedule': 3600.0,  # Every hour
    },
}
```

### Start Beat Scheduler

```bash
celery -A celery_worker.celery_app beat --loglevel=info
```

## Production Deployment

### Using Supervisor

Create `/etc/supervisor/conf.d/celery.conf`:

```ini
[program:celery_worker]
command=/home/gurpyar/Documents/R/REIMS2/backend/venv/bin/celery -A celery_worker.celery_app worker --loglevel=info
directory=/home/gurpyar/Documents/R/REIMS2/backend
user=gurpyar
numprocs=1
stdout_logfile=/var/log/celery/worker.log
stderr_logfile=/var/log/celery/worker.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600
```

### Using Docker

See Docker Compose configuration for containerized deployment.

## Troubleshooting

### Worker not picking up tasks

1. Check Redis is running:
   ```bash
   docker ps | grep redis
   ```

2. Check worker logs:
   ```bash
   tail -f /tmp/celery_worker.log
   ```

3. Verify broker connection:
   ```bash
   celery -A celery_worker.celery_app inspect ping
   ```

### Task stuck in PENDING

- Worker might not be running
- Task name mismatch
- Redis connection issues

### Check Active Workers

```bash
celery -A celery_worker.celery_app inspect active
```

### Purge All Tasks

```bash
celery -A celery_worker.celery_app purge
```

## Configuration

All Celery configuration is in `app/core/celery_config.py`:

- Broker: Redis (localhost:6379)
- Backend: Redis (localhost:6379)
- Serialization: JSON
- Time limits: 30 minutes hard, 25 minutes soft
- Result expiration: 1 hour

## Best Practices

1. **Keep tasks idempotent** - Running the same task multiple times should produce the same result
2. **Set reasonable timeouts** - Prevent tasks from running forever
3. **Use retry mechanisms** - Handle temporary failures gracefully
4. **Monitor tasks** - Use Flower or logs to track task execution
5. **Don't pass large data** - Pass references (IDs) instead of large objects
6. **Use dedicated queues** - Separate critical from non-critical tasks

## Resources

- Celery Documentation: https://docs.celeryproject.org/
- Flower Documentation: https://flower.readthedocs.io/

