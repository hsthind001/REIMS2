#!/usr/bin/env python3
"""
Retry failed balance sheet extractions for 2023, 2024, 2025
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.models.financial_period import FinancialPeriod
from app.tasks.extraction_tasks import extract_document


def retry_failed_balance_sheets():
    """
    Retry extraction for all failed balance sheet documents from 2023-2025
    """
    db: Session = SessionLocal()

    try:
        # Query failed balance sheet documents from 2023-2025
        failed_docs = db.query(DocumentUpload).join(
            FinancialPeriod, DocumentUpload.period_id == FinancialPeriod.id
        ).filter(
            DocumentUpload.document_type == 'balance_sheet',
            DocumentUpload.extraction_status.in_(['failed', 'failed_validation']),
            FinancialPeriod.period_year.in_([2023, 2024, 2025])
        ).order_by(
            FinancialPeriod.period_year,
            FinancialPeriod.period_month
        ).all()

        print(f"Found {len(failed_docs)} failed balance sheet documents to retry")
        print("=" * 80)

        success_count = 0
        error_count = 0

        for doc in failed_docs:
            period = db.query(FinancialPeriod).filter(FinancialPeriod.id == doc.period_id).first()
            
            print(f"\n📄 Processing Upload ID: {doc.id}")
            print(f"   File: {doc.file_name}")
            print(f"   Period: {period.period_year}-{period.period_month:02d}")
            print(f"   Current Status: {doc.extraction_status}")

            try:
                # Reset status to pending
                doc.extraction_status = 'pending'
                db.commit()

                # Trigger Celery task
                task = extract_document.delay(doc.id)

                print(f"   ✅ Task triggered: {task.id}")
                print(f"   Status: pending → processing")
                success_count += 1

            except Exception as e:
                print(f"   ❌ Error triggering extraction: {e}")
                error_count += 1
                # Rollback on error
                db.rollback()

        print("\n" + "=" * 80)
        print(f"✅ Successfully triggered: {success_count} extractions")
        if error_count > 0:
            print(f"❌ Failed to trigger: {error_count} extractions")
        print(f"📊 Total: {len(failed_docs)} documents")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    print("🔄 Retrying failed balance sheet extractions...")
    print("=" * 80)
    retry_failed_balance_sheets()
    print("\n✅ Done!")

