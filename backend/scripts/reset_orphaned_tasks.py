#!/usr/bin/env python3
"""
Reset Orphaned Extraction Tasks

This script finds document uploads stuck in 'processing' status and resets them
to 'pending' so they can be retried. This happens when Celery tasks are interrupted
during shutdown or due to worker crashes.

Can be run:
1. Automatically on backend startup (via entrypoint.sh)
2. Manually: docker exec reims-backend python3 /app/scripts/reset_orphaned_tasks.py
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.document_upload import DocumentUpload
from app.core.config import settings
from datetime import datetime, timedelta, timezone
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_database_url():
    """Build database URL from settings"""
    return f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"


def reset_orphaned_tasks():
    """
    Find and reset orphaned tasks
    
    Criteria for orphaned task:
    - extraction_status = 'processing'
    - extraction_started_at is older than 10 minutes (or None)
    
    Returns:
        int: Number of tasks reset
    """
    try:
        # Create database connection
        engine = create_engine(get_database_url())
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        logger.info("🔍 Checking for orphaned extraction tasks...")
        
        # Find all documents stuck in processing
        orphaned_uploads = db.query(DocumentUpload).filter(
            DocumentUpload.extraction_status == 'processing'
        ).all()
        
        if not orphaned_uploads:
            logger.info("✅ No orphaned tasks found - all clear!")
            db.close()
            return 0
        
        # Calculate time threshold (10 minutes ago)
        time_threshold = datetime.now(timezone.utc) - timedelta(minutes=10)
        
        reset_count = 0
        for upload in orphaned_uploads:
            # Check if truly orphaned (started more than 10 minutes ago or never started)
            is_orphaned = (
                upload.extraction_started_at is None or 
                upload.extraction_started_at < time_threshold
            )
            
            if is_orphaned:
                logger.info(
                    f"🔄 Resetting orphaned task: "
                    f"upload_id={upload.id}, "
                    f"file={upload.file_name}, "
                    f"started_at={upload.extraction_started_at}"
                )
                
                # Reset to pending
                upload.extraction_status = 'pending'
                upload.extraction_started_at = None
                upload.extraction_completed_at = None
                
                reset_count += 1
            else:
                logger.info(
                    f"⏳ Task still active (< 10 min): "
                    f"upload_id={upload.id}, "
                    f"file={upload.file_name}"
                )
        
        # Commit changes
        if reset_count > 0:
            db.commit()
            logger.info(f"✅ Reset {reset_count} orphaned task(s) to 'pending' status")
            logger.info("🔄 Celery worker will automatically retry these tasks")
        else:
            logger.info("ℹ️  All 'processing' tasks are still active (< 10 minutes old)")
        
        db.close()
        return reset_count
        
    except Exception as e:
        logger.error(f"❌ Error resetting orphaned tasks: {e}")
        logger.exception(e)
        return 0


if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("🧹 ORPHANED TASK CLEANUP SCRIPT")
    logger.info("=" * 70)
    
    reset_count = reset_orphaned_tasks()
    
    logger.info("=" * 70)
    logger.info(f"✅ Cleanup complete: {reset_count} task(s) reset")
    logger.info("=" * 70)
    
    sys.exit(0)

