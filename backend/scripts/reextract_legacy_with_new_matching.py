"""
Re-extract Legacy Documents with New Match Confidence Tracking

Re-extracts documents that were uploaded before the match_confidence and 
match_strategy fields were added, allowing them to benefit from:
- Separate extraction and match confidence tracking
- Match strategy visibility
- Enhanced needs_review logic

Targets documents with:
- match_confidence = 0 (backfilled, not real)
- match_strategy = 'legacy_match' or 'unmatched'
- extraction_completed_at before migration date

Usage:
    python3 scripts/reextract_legacy_with_new_matching.py --dry-run
    python3 scripts/reextract_legacy_with_new_matching.py --execute --year 2024 --type balance_sheet
"""
import sys
import os
import argparse
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.balance_sheet_data import BalanceSheetData
from app.models.cash_flow_data import CashFlowData
from app.tasks.extraction_tasks import extract_document
from sqlalchemy import or_


def reextract_legacy_documents(document_type=None, year=None, dry_run=True):
    """Re-extract legacy documents with new matching logic"""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("RE-EXTRACT LEGACY DOCUMENTS WITH NEW MATCH TRACKING")
        print("=" * 80)
        
        # Migration date (when match_confidence fields were added)
        MIGRATION_DATE = datetime(2025, 11, 6, 15, 0, 0)
        
        # Query for legacy documents
        query = db.query(
            DocumentUpload,
            Property.property_code,
            FinancialPeriod.period_year,
            FinancialPeriod.period_month
        ).join(
            Property, DocumentUpload.property_id == Property.id
        ).join(
            FinancialPeriod, DocumentUpload.period_id == FinancialPeriod.id
        ).filter(
            DocumentUpload.extraction_status == 'completed',
            DocumentUpload.extraction_completed_at < MIGRATION_DATE,
            DocumentUpload.document_type.in_(['balance_sheet', 'cash_flow'])  # Skip income_statement (just uploaded)
        )
        
        # Apply filters
        if document_type:
            query = query.filter(DocumentUpload.document_type == document_type)
        if year:
            query = query.filter(FinancialPeriod.period_year == year)
        
        results = query.all()
        
        print(f"\n📊 Found {len(results)} legacy documents to re-extract")
        
        if not results:
            print("✅ No legacy documents need re-extraction!")
            return
        
        print("\n" + "=" * 80)
        print("LEGACY DOCUMENTS:")
        print("=" * 80)
        print(f"{'ID':<8} {'Type':<18} {'Property':<12} {'Period':<12} {'Extracted':<20}")
        print("-" * 80)
        
        for upload, prop_code, year, month in results[:20]:
            extracted_date = upload.extraction_completed_at.strftime('%Y-%m-%d %H:%M') if upload.extraction_completed_at else 'N/A'
            print(f"{upload.id:<8} {upload.document_type:<18} {prop_code:<12} {year}-{month:02d}      {extracted_date:<20}")
        
        if len(results) > 20:
            print(f"... and {len(results) - 20} more documents")
        
        print("-" * 80)
        
        if dry_run:
            print("\n🔍 DRY RUN MODE - No changes made")
            print(f"   Would re-extract {len(results)} documents")
            print("\n💡 To execute, run with --execute flag")
            print("\n⚠️  WARNING: Re-extraction will:")
            print("   - Delete existing extracted data")
            print("   - Re-trigger extraction with new matching logic")
            print("   - May take several minutes to complete")
            print("\n📋 Recommended: Backup database first!")
        else:
            print(f"\n🚀 EXECUTING: Re-extracting {len(results)} documents...")
            print("⚠️  This may take several minutes...\n")
            
            success_count = 0
            error_count = 0
            
            for idx, (upload, prop_code, year, month) in enumerate(results, 1):
                try:
                    print(f"[{idx}/{len(results)}] Re-extracting {upload.document_type} {prop_code} {year}-{month:02d} (ID: {upload.id})...")
                    
                    # Delete old data
                    if upload.document_type == 'balance_sheet':
                        deleted = db.query(BalanceSheetData).filter(
                            BalanceSheetData.upload_id == upload.id
                        ).delete()
                    elif upload.document_type == 'cash_flow':
                        deleted = db.query(CashFlowData).filter(
                            CashFlowData.upload_id == upload.id
                        ).delete()
                    
                    print(f"   - Deleted {deleted} old records")
                    
                    # Reset upload status
                    upload.extraction_status = 'pending'
                    upload.extraction_started_at = None
                    upload.extraction_completed_at = None
                    
                    db.commit()
                    
                    # Trigger new extraction
                    task = extract_document.delay(upload.id)
                    print(f"   ✅ Task queued: {task.id}")
                    success_count += 1
                    
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    db.rollback()
                    error_count += 1
            
            print("\n" + "=" * 80)
            print(f"✅ Re-extraction queued:")
            print(f"   - Success: {success_count}")
            print(f"   - Errors: {error_count}")
            print("\n💡 Monitor progress:")
            print("   - celery -A app.core.celery_config inspect active")
            print("   - Check /api/v1/quality/statistics/yearly for updated metrics")
            print("=" * 80)
        
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Re-extract legacy documents')
    parser.add_argument('--dry-run', action='store_true', help='Preview without executing')
    parser.add_argument('--execute', action='store_true', help='Execute re-extraction')
    parser.add_argument('--type', choices=['balance_sheet', 'cash_flow'], help='Document type to re-extract')
    parser.add_argument('--year', type=int, help='Filter by year (e.g., 2024)')
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.execute:
        args.dry_run = True
    
    reextract_legacy_documents(
        document_type=args.type,
        year=args.year,
        dry_run=args.dry_run
    )

