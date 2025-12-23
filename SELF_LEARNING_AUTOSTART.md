# Self-Learning System Auto-Start Configuration

## Overview

The self-learning and self-improving functionality is now **automatically enabled** when REIMS services start. The system runs continuously in the background, learning from issues and preventing recurrence.

## Automatic Components

### 1. **Backend Initialization** (`backend/app/main.py`)
- On backend startup, the system verifies self-learning tables are accessible
- Logs initialization status to confirm the system is ready
- No manual intervention required

### 2. **Celery Beat Scheduler** (`docker-compose.yml`)
- **New Service**: `celery-beat` container runs automatically
- Schedules periodic learning tasks
- Restarts automatically if it stops
- Health checks ensure it's running

### 3. **Scheduled Learning Tasks**

#### **Analyze Captured Issues**
- **Schedule**: Every 6 hours
- **Task**: `app.tasks.learning_tasks.analyze_captured_issues`
- **Purpose**: Analyzes captured issues to identify patterns and create prevention rules
- **Location**: `backend/app/tasks/learning_tasks.py`

#### **Sync MCP Tasks**
- **Schedule**: Every 2 hours
- **Task**: `app.tasks.learning_tasks.sync_mcp_tasks`
- **Purpose**: Syncs learned fixes with task-master-ai MCP server and creates tasks for critical issues
- **Location**: `backend/app/tasks/learning_tasks.py`

#### **Cleanup Old Issues**
- **Schedule**: Daily at 3:00 AM UTC
- **Task**: `app.tasks.learning_tasks.cleanup_old_issues`
- **Purpose**: Archives old resolved issues and deletes old captures (keeps for 30 days)
- **Location**: `backend/app/tasks/learning_tasks.py`

## Docker Services

When you run `docker compose up`, the following services start automatically:

1. **backend**: FastAPI application (includes self-learning initialization)
2. **celery-worker**: Processes background tasks
3. **celery-beat**: Schedules periodic learning tasks ⭐ **NEW**
4. **flower**: Celery monitoring (optional)
5. Other services (postgres, redis, minio, frontend)

## Verification

### Check if Celery Beat is Running
```bash
docker compose ps celery-beat
```

### Check Scheduled Tasks
```bash
docker compose logs celery-beat | grep -i "beat"
```

### Check Learning Task Execution
```bash
docker compose logs celery-worker | grep -i "learning"
```

### View Self-Learning Statistics
```bash
curl http://localhost:8000/api/v1/self-learning/stats
```

## Manual Task Execution (Optional)

If you need to manually trigger learning tasks:

```bash
# Analyze issues now
docker compose exec celery-worker celery -A celery_worker.celery_app call app.tasks.learning_tasks.analyze_captured_issues

# Sync MCP tasks now
docker compose exec celery-worker celery -A celery_worker.celery_app call app.tasks.learning_tasks.sync_mcp_tasks

# Cleanup old issues now
docker compose exec celery-worker celery -A celery_worker.celery_app call app.tasks.learning_tasks.cleanup_old_issues
```

## Configuration

### Schedule Customization

Edit `backend/app/core/celery_config.py` to change schedules:

```python
celery_app.conf.beat_schedule = {
    'analyze-captured-issues': {
        'task': 'app.tasks.learning_tasks.analyze_captured_issues',
        'schedule': crontab(hour='*/6', minute=0),  # Change schedule here
    },
    # ... other tasks
}
```

### Task Parameters

Tasks accept parameters that can be customized:

- `analyze_captured_issues(days_back=7, min_occurrences=3)`
- `sync_mcp_tasks(tag="self-learning")`
- `cleanup_old_issues(days_to_keep=90)`

## What Happens Automatically

1. **On Service Start**:
   - Backend verifies self-learning tables exist
   - Celery Beat starts and loads scheduled tasks
   - System is ready to capture and learn from issues

2. **During Operation**:
   - Issues are automatically captured during document uploads/extractions
   - Pre-flight checks prevent known issues before they occur
   - Auto-fixes apply learned solutions automatically

3. **Periodically** (via Celery Beat):
   - Issues are analyzed for patterns (every 6 hours)
   - MCP tasks are synced (every 2 hours)
   - Old issues are archived (daily at 3 AM)

4. **On Issue Resolution**:
   - Fixes are documented in the knowledge base
   - Prevention rules are generated automatically
   - MCP tasks are updated with resolution details

## Troubleshooting

### Celery Beat Not Starting
```bash
# Check logs
docker compose logs celery-beat

# Restart service
docker compose restart celery-beat
```

### Tasks Not Running
```bash
# Check if tasks are registered
docker compose exec celery-worker celery -A celery_worker.celery_app inspect registered | grep learning

# Check beat schedule
docker compose exec celery-beat celery -A celery_worker.celery_app inspect scheduled
```

### Database Connection Issues
- Ensure postgres service is healthy: `docker compose ps postgres`
- Check database credentials in `.env` file
- Verify migrations ran: `docker compose logs db-init`

## Summary

✅ **Self-learning system is fully automated**
✅ **No manual intervention required**
✅ **Runs automatically when REIMS services start**
✅ **Continuously learns and improves**
✅ **Prevents known issues from recurring**

The system is now production-ready and will automatically maintain and improve itself!

