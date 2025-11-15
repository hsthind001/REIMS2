#!/usr/bin/env python3
"""
Trigger extraction for all pending documents
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.tasks.extraction_tasks import extract_document


def trigger_pending_extractions(document_type=None):
    """
    Trigger extraction for all pending documents

    Args:
        document_type: Optional filter by document type (e.g., 'rent_roll')
    """
    db: Session = SessionLocal()

    try:
        # Query pending documents
        query = db.query(DocumentUpload).filter(
            DocumentUpload.extraction_status == 'pending'
        )

        if document_type:
            query = query.filter(DocumentUpload.document_type == document_type)

        pending_docs = query.all()

        print(f"Found {len(pending_docs)} pending documents")

        for doc in pending_docs:
            print(f"\nTriggering extraction for:")
            print(f"  ID: {doc.id}")
            print(f"  Type: {doc.document_type}")
            print(f"  File: {doc.file_name}")
            print(f"  Property ID: {doc.property_id}")
            print(f"  Period ID: {doc.period_id}")

            try:
                # Update status to processing
                doc.extraction_status = 'processing'
                db.commit()

                # Trigger Celery task
                task = extract_document.delay(
                    upload_id=doc.id
                )

                print(f"  Task ID: {task.id}")
                print(f"  ✓ Extraction triggered successfully")

            except Exception as e:
                print(f"  ✗ Error triggering extraction: {e}")
                doc.extraction_status = 'pending'
                db.commit()

        print(f"\n✓ Triggered extraction for {len(pending_docs)} documents")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Trigger extraction for pending documents')
    parser.add_argument('--type', help='Filter by document type (rent_roll, balance_sheet, etc.)')
    args = parser.parse_args()

    trigger_pending_extractions(document_type=args.type)
