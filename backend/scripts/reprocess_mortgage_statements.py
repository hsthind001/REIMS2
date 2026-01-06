#!/usr/bin/env python3
"""
Re-process Failed Mortgage Statement Uploads

All 10 mortgage statement uploads show "completed" status but have 0 records
due to transaction errors during initial extraction. This script re-processes
them to extract and save the data correctly.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.models.mortgage_statement_data import MortgageStatementData
from app.services.extraction_orchestrator import ExtractionOrchestrator


def reprocess_mortgage_statements():
    """Re-process all mortgage statement uploads"""

    print("=" * 80)
    print("Re-process Failed Mortgage Statement Uploads")
    print("=" * 80)
    print()

    session = SessionLocal()

    try:
        # Get all mortgage statement uploads
        mortgage_uploads = session.query(DocumentUpload).filter(
            DocumentUpload.document_type == 'mortgage_statement'
        ).order_by(DocumentUpload.id).all()

        print(f"📊 Found {len(mortgage_uploads)} mortgage statement uploads")
        print()

        # Check current state
        total_records = session.query(MortgageStatementData).count()
        print(f"Current mortgage records in database: {total_records}")
        print()

        if total_records > 0:
            print("ℹ️  Note: Some records already exist. This will DELETE and REPLACE them.")
            print()

        # Re-process each upload
        orchestrator = ExtractionOrchestrator(session)

        successful = 0
        failed = 0
        total_records_created = 0

        print("🔄 Re-processing uploads...")
        print()

        for i, upload in enumerate(mortgage_uploads, 1):
            print(f"[{i}/{len(mortgage_uploads)}] Processing Upload ID {upload.id}: {upload.file_name}")
            print(f"    Property: {upload.property_id}, Period: {upload.period_id}")

            try:
                # Reset upload status
                upload.extraction_status = "processing"
                upload.notes = None
                session.commit()

                # Re-run extraction
                result = orchestrator.extract_document(upload.id)

                if result.get("success"):
                    successful += 1

                    # Count records created
                    records = session.query(MortgageStatementData).filter(
                        MortgageStatementData.upload_id == upload.id
                    ).count()

                    total_records_created += records
                    print(f"    ✅ Success - {records} records created")
                else:
                    failed += 1
                    error = result.get("error", "Unknown error")
                    print(f"    ❌ Failed: {error}")

            except Exception as e:
                failed += 1
                print(f"    ❌ Exception: {str(e)}")
                # Rollback this upload's transaction
                session.rollback()
                session = SessionLocal()  # Get new session
                orchestrator = ExtractionOrchestrator(session)  # New orchestrator

            print()

        # Summary
        print("=" * 80)
        print("RE-PROCESSING COMPLETE")
        print("=" * 80)
        print(f"Total uploads: {len(mortgage_uploads)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Total records created: {total_records_created}")
        print()

        if successful == len(mortgage_uploads):
            print("🎉 All mortgage statements successfully re-processed!")
        elif successful > 0:
            print(f"✅ {successful} uploads processed successfully")
            print(f"⚠️  {failed} uploads still failing")
        else:
            print("❌ All re-processing attempts failed")
            print("   Check extraction_orchestrator.py for mortgage statement handling")

        print()

        # Final verification
        final_records = session.query(MortgageStatementData).count()
        print(f"Final mortgage records in database: {final_records}")

        if final_records > 0:
            print(f"Match rate will update automatically (records/documents = {final_records}/{len(mortgage_uploads)})")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    reprocess_mortgage_statements()
