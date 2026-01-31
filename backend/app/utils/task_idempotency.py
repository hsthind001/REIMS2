"""
Task idempotency utilities for Celery (P1).
Uses Redis lock to prevent duplicate execution of the same logical operation.
"""
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def acquire_extraction_lock(upload_id: int, task_id: str, ttl_seconds: int = 600) -> bool:
    """
    Acquire a distributed lock for extraction task.
    Returns True if lock acquired, False if another task holds it (duplicate).
    """
    try:
        from app.db.redis_client import get_redis
        redis = get_redis()
        key = f"extract_lock:{upload_id}"
        acquired = redis.set(key, task_id, nx=True, ex=ttl_seconds)
        if not acquired:
            logger.info(f"Extraction task for upload_id={upload_id} skipped (duplicate, lock held)")
        return bool(acquired)
    except Exception as e:
        logger.warning(f"Redis lock check failed for upload_id={upload_id}: {e}, proceeding")
        return True


def acquire_job_lock(job_id: int, task_id: str, ttl_seconds: int = 7200) -> bool:
    """Acquire lock for batch job. Returns True if acquired."""
    try:
        from app.db.redis_client import get_redis
        redis = get_redis()
        key = f"reprocess_job:{job_id}"
        acquired = redis.set(key, task_id, nx=True, ex=ttl_seconds)
        return bool(acquired)
    except Exception as e:
        logger.warning(f"Redis job lock failed for job_id={job_id}: {e}")
        return True


def release_job_lock(job_id: int, task_id: str) -> None:
    """Release batch job lock if we hold it."""
    try:
        from app.db.redis_client import get_redis
        redis = get_redis()
        key = f"reprocess_job:{job_id}"
        current = redis.get(key)
        if current == task_id:
            redis.delete(key)
    except Exception as e:
        logger.warning(f"Redis job lock release failed for job_id={job_id}: {e}")


def release_extraction_lock(upload_id: int, task_id: str) -> None:
    """Release lock only if we hold it (match task_id)."""
    try:
        from app.db.redis_client import get_redis
        redis = get_redis()
        key = f"extract_lock:{upload_id}"
        current = redis.get(key)
        if current == task_id:
            redis.delete(key)
    except Exception as e:
        logger.warning(f"Redis lock release failed for upload_id={upload_id}: {e}")
