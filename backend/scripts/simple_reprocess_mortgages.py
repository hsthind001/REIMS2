#!/usr/bin/env python3
"""
Simple Re-process Mortgage Statements

Simplified approach: Just mark uploads as "pending" and let the system
re-extract them using the standard extraction pipeline.
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


def simple_reprocess():
    """Mark uploads as pending for re-processing"""

    print("=" * 80)
    print("Simple Re-process Mortgage Statements")
    print("=" * 80)
    print()

    session = SessionLocal()

    try:
        # Mark Upload ID 4 as failed (file missing)
        print("Step 1: Mark missing file upload as failed...")
        upload_4 = session.query(DocumentUpload).filter(DocumentUpload.id == 4).first()
        if upload_4:
            upload_4.extraction_status = "failed"
            upload_4.notes = "PDF file missing from MinIO (ESP_2023_02_Mortgage_Statement.pdf)"
            session.commit()
            print(f"✅ Upload ID 4 marked as failed")
        print()

        # Get the 9 valid uploads
        valid_ids = [49, 50, 51, 52, 53, 54, 55, 56, 57]
        uploads = session.query(DocumentUpload).filter(
            DocumentUpload.id.in_(valid_ids)
        ).all()

        print(f"Step 2: Mark {len(uploads)} uploads as pending for re-processing...")
        print()

        for upload in uploads:
            upload.extraction_status = "pending"
            upload.notes = "Marked for re-extraction via API"

        session.commit()
        print(f"✅ {len(uploads)} uploads marked as pending")
        print()

        print("=" * 80)
        print("INSTRUCTIONS")
        print("=" * 80)
        print()
        print("The 9 mortgage statement uploads have been marked as 'pending'.")
        print("To complete the extraction, trigger re-processing via the API:")
        print()
        print("Option 1: Use the frontend to re-upload the documents")
        print("Option 2: Call the extraction API endpoint for each upload:")
        for upload_id in valid_ids:
            print(f"  POST /api/v1/extraction/extract/{upload_id}")
        print()
        print("Or we can trigger extraction programmatically...")
        print()

        # Ask if we should trigger extraction now
        print("Attempting automatic extraction...")
        print()

        from app.services.extraction_orchestrator import ExtractionOrchestrator

        successful = 0
        failed = 0

        for i, upload_id in enumerate(valid_ids, 1):
            print(f"[{i}/{len(valid_ids)}] Extracting Upload ID {upload_id}...")

            # Get fresh upload from DB
            session_new = SessionLocal()
            try:
                upload = session_new.query(DocumentUpload).filter(
                    DocumentUpload.id == upload_id
                ).first()

                if not upload:
                    print(f"    ❌ Upload not found")
                    continue

                orchestrator = ExtractionOrchestrator(session_new)
                result = orchestrator.extract_and_parse_document(upload_id)

                if result.get("success"):
                    successful += 1
                    print(f"    ✅ Success")
                else:
                    failed += 1
                    error = result.get("error", "Unknown error")
                    print(f"    ❌ Failed: {error[:100]}")

            except Exception as e:
                failed += 1
                print(f"    ❌ Exception: {str(e)[:100]}")
            finally:
                session_new.close()

            print()

        # Final summary
        print("=" * 80)
        print("EXTRACTION COMPLETE")
        print("=" * 80)
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print()

        # Check final state
        total_records = session.query(MortgageStatementData).count()
        print(f"Total mortgage records in database: {total_records}")

        if total_records > 0:
            print()
            print("🎉 Mortgage statements successfully extracted!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    simple_reprocess()
