#!/usr/bin/env python3
"""
Re-queue pending document extractions

This script finds all document uploads with status='pending' and triggers
Celery extraction tasks for them.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.tasks.extraction_tasks import extract_document


def requeue_pending_extractions():
    """Find pending documents and queue extraction tasks"""
    db: Session = SessionLocal()
    
    try:
        # Find all pending uploads
        pending_uploads = db.query(DocumentUpload).filter(
            DocumentUpload.extraction_status == "pending"
        ).all()
        
        if not pending_uploads:
            print("✅ No pending uploads found!")
            return
        
        print(f"📊 Found {len(pending_uploads)} pending uploads")
        print("\n🔄 Queueing extraction tasks...\n")
        
        queued = 0
        for upload in pending_uploads:
            try:
                task = extract_document.delay(upload.id)
                print(f"  ✓ Upload #{upload.id} ({upload.document_type}) - Task ID: {task.id}")
                queued += 1
            except Exception as e:
                print(f"  ✗ Upload #{upload.id} - Error: {str(e)}")
        
        print(f"\n✅ Queued {queued}/{len(pending_uploads)} extraction tasks")
        
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 70)
    print("REIMS2 - Re-queue Pending Extractions")
    print("=" * 70)
    print()
    
    requeue_pending_extractions()
    
    print()
    print("=" * 70)
    print("Monitor Celery worker with: docker logs reims-celery-worker -f")
    print("Monitor Flower dashboard: http://localhost:5555")
    print("=" * 70)
