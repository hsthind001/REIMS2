#!/usr/bin/env python
"""
Celery Worker Entry Point

Run with:
    celery -A celery_worker.celery_app worker --loglevel=info

Or with specific queue:
    celery -A celery_worker.celery_app worker --loglevel=info -Q default,email
"""

from app.core.celery_config import celery_app

if __name__ == "__main__":
    celery_app.start()

