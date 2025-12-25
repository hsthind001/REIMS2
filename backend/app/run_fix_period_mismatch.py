#!/usr/bin/env python3
"""
Quick Fix Script for Upload Period Mismatches
Run directly via docker compose exec
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.models.financial_period import FinancialPeriod
from app.models.mortgage_statement_data import MortgageStatementData
import re
from datetime import datetime


def extract_date_from_filename(filename: str):
    """Extract year and month from filename"""
    patterns = [
        r'(\d{4})\.(\d{2})\.(\d{2})',  # 2023.02.06
        r'(\d{4})_(\d{2})_(\d{2})',    # 2023_02_06
    ]

    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            groups = match.groups()
            if len(groups) >= 2:
                year = int(groups[0])
                month = int(groups[1])
                return year, month

    return None, None


def main():
    db = SessionLocal()

    try:
        print("\n" + "="*80)
        print("FIXING UPLOAD PERIOD MISMATCHES")
        print("="*80)

        # Get all mortgage statement uploads for ESP001
        uploads = db.query(DocumentUpload).filter(
            DocumentUpload.document_type == 'mortgage_statement',
            DocumentUpload.property_id == 1  # ESP001
        ).order_by(DocumentUpload.id).all()

        print(f"\nFound {len(uploads)} mortgage statement uploads")

        fixes = []

        for upload in uploads:
            # Extract date from filename
            year, month = extract_date_from_filename(upload.file_name)

            if year and month:
                # Get current period
                current_period = db.query(FinancialPeriod).filter(
                    FinancialPeriod.id == upload.period_id
                ).first()

                # Find correct period
                correct_period = db.query(FinancialPeriod).filter(
                    FinancialPeriod.property_id == upload.property_id,
                    FinancialPeriod.period_year == year,
                    FinancialPeriod.period_month == month
                ).first()

                if current_period and correct_period and current_period.id != correct_period.id:
                    fixes.append({
                        'upload_id': upload.id,
                        'filename': upload.file_name,
                        'from_period': current_period.period_month,
                        'to_period': correct_period.period_month,
                        'from_period_id': current_period.id,
                        'to_period_id': correct_period.id
                    })
                    print(f"\n  Upload ID {upload.id}: {upload.file_name}")
                    print(f"    Wrong Period: {current_period.period_month} (ID={current_period.id})")
                    print(f"    Correct Period: {correct_period.period_month} (ID={correct_period.id})")

        if not fixes:
            print("\n✅ No period mismatches found!")
            return 0

        print(f"\n\n⚠️  Found {len(fixes)} period mismatches")
        print("\n" + "="*80)
        print("APPLYING FIXES (in reverse order to avoid collisions)...")
        print("="*80)

        # Process in reverse order to avoid unique constraint violations
        # Since all uploads are off by -1, we need to shift from highest to lowest
        # COMMIT AFTER EACH UPDATE to avoid batch constraint violations
        for fix in reversed(fixes):
            upload = db.query(DocumentUpload).filter(
                DocumentUpload.id == fix['upload_id']
            ).first()

            # Update upload period
            old_period_id = upload.period_id
            upload.period_id = fix['to_period_id']

            # Update mortgage data if exists
            mortgage = db.query(MortgageStatementData).filter(
                MortgageStatementData.upload_id == fix['upload_id']
            ).first()

            if mortgage:
                mortgage.period_id = fix['to_period_id']

            # CRITICAL: Commit after EACH update to avoid constraint violations
            db.commit()

            if mortgage:
                print(f"\n  ✓ Fixed Upload {fix['upload_id']}: Period {fix['from_period']} → {fix['to_period']}")
                print(f"    Updated document_upload and mortgage_statement_data")
            else:
                print(f"\n  ✓ Fixed Upload {fix['upload_id']}: Period {fix['from_period']} → {fix['to_period']}")
                print(f"    Updated document_upload (no mortgage data yet)")

        print("\n" + "="*80)
        print(f"✅ SUCCESS: Fixed {len(fixes)} period mismatches")
        print("="*80)

        return 0

    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return 1
    finally:
        db.close()


if __name__ == '__main__':
    sys.exit(main())
