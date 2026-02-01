# Celery Queues and Document Extraction

This document describes how document extraction is wired to Celery and how to ensure it keeps working across REIMS restarts. **If the main Celery worker does not consume the `extraction` queue, all uploaded documents will stay in "pending" forever.**

## Why extraction and analytics queues are required

- **Document extraction:** When a document is uploaded, the API calls `extract_document.delay(upload_id)` and sets the upload status to `pending`. These tasks are routed to the **`extraction`** queue. If no worker consumes `extraction`, documents stay pending forever.
- **Batch jobs (e.g. Anomaly Reprocessing):** Jobs like AN_001 use `reprocess_documents_batch`, which is routed to the **`analytics`** queue. If no worker consumes `analytics`, the job shows RUNNING but Total/Processed stay 0 and the task never runs.
- **Task routing:** In `app/core/celery_config.py`, extraction tasks go to `extraction`; batch reprocessing, nightly anomaly detection, and learning tasks go to `analytics`.
- **Worker consumption:** The main worker must be started with **`-Q celery,extraction,analytics`** so it consumes all three. Missing `extraction` → documents stuck pending. Missing `analytics` → batch jobs stuck at 0% progress.

## Required configuration (persistent)

### 1. Main Celery worker (`docker-compose.yml`)

The main worker **must** include the `extraction` and `analytics` queues:

```bash
celery -A celery_worker.celery_app worker --loglevel=info -Q celery,extraction,analytics
```

**Do not remove `extraction` or `analytics`.** Without `extraction`, document uploads stay pending. Without `analytics`, batch jobs (e.g. Anomaly Reprocessing) show RUNNING but never process (0% progress).

### 2. Recovery tasks (automatic after restart)

- **Document extraction:** `recover_stuck_extractions` runs **every minute** via Celery Beat. Finds uploads that are still `pending` and either have no task ID or have been pending for **2+ minutes**, then re-queues `extract_document` for them.
- **Batch jobs:** `recover_stuck_batch_jobs` runs **every minute** via Celery Beat. Finds batch jobs in `running` with **0 progress** for **2+ minutes**, then re-queues `reprocess_documents_batch` for them (e.g. task was lost when worker was not consuming the analytics queue).

So:

- **Worker must consume `extraction` and `analytics`** → ensures new uploads, batch jobs, and re-queued tasks are processed.
- **Recovery tasks + 2‑minute stale threshold** → within about 2 minutes after a restart, stuck pending documents and stuck running batch jobs are re-queued automatically.
- **Manual requeue:** For a single stuck batch job, use **Requeue** in the Batch Jobs UI or `POST /api/v1/batch-reprocessing/jobs/{job_id}/requeue` (requires job running 2+ min with 0 progress).

## Redis and queue persistence

- Redis uses the **`redis-data`** Docker volume. With the default `docker compose down` (no `-v`), Redis data and the Celery queues persist across restarts.
- If you run `docker compose down -v`, volumes are removed and the queue is cleared; the recovery task will still re-queue pending documents (2+ min old) within a couple of minutes.

## If documents stay pending after a restart

1. **Check worker queues:**  
   `docker compose exec celery-worker ps aux` (or inspect the process command). You should see `-Q celery,extraction`.
2. **Check recovery task:**  
   `docker compose logs celery-worker` and look for `recover_stuck_extractions` and "Found N stuck upload(s)". It runs every minute.
3. **Restart the worker** so it loads the correct queue list:  
   `docker compose restart celery-worker`.
4. Wait 2–3 minutes and refresh the Data Control Center; pending documents should move to Extracting then Completed (or Failed).

## Reference

- Task routes: `backend/app/core/celery_config.py` (`task_routes`, extraction → `extraction`, batch/analytics → `analytics`).
- Recovery tasks: `backend/app/tasks/extraction_tasks.py` (`recover_stuck_extractions`), `backend/app/tasks/batch_reprocessing_tasks.py` (`recover_stuck_batch_jobs`); stale threshold 2 minutes for both.
- Beat schedule: `backend/app/core/celery_config.py` (`recover-stuck-extractions`, `recover-stuck-batch-jobs` every minute).
