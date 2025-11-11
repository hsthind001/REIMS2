"""
Re-extract Cash Flow Documents with Low Match Rates

Identifies and re-extracts cash flow uploads that have low match rates,
allowing them to benefit from:
- Newly added accounts in chart_of_accounts
- Enhanced intelligent matching logic
- Separate match_confidence tracking

Usage:
    python3 scripts/reextract_low_match_cash_flows.py --dry-run  # Preview
    python3 scripts/reextract_low_match_cash_flows.py --execute  # Run

"""
import sys
import os
import argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.models.cash_flow_data import CashFlowData
from app.models.financial_period import FinancialPeriod
from app.models.property import Property
from app.tasks.extraction_tasks import extract_document
from sqlalchemy import func


def reextract_low_match_cash_flows(dry_run=True):
    """Re-extract cash flow documents with low match rates"""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("RE-EXTRACT LOW MATCH CASH FLOW DOCUMENTS")
        print("=" * 80)
        
        # Find cash flow uploads with low match rates
        # Calculate match rate per upload
        upload_stats = db.query(
            DocumentUpload.id.label('upload_id'),
            Property.property_code,
            FinancialPeriod.period_year,
            FinancialPeriod.period_month,
            func.count(CashFlowData.id).label('total_records'),
            func.count(CashFlowData.account_id).label('matched_records'),
            DocumentUpload.extraction_status
        ).join(
            Property, DocumentUpload.property_id == Property.id
        ).join(
            FinancialPeriod, DocumentUpload.period_id == FinancialPeriod.id
        ).outerjoin(
            CashFlowData, CashFlowData.upload_id == DocumentUpload.id
        ).filter(
            DocumentUpload.document_type == 'cash_flow',
            DocumentUpload.extraction_status == 'completed'
        ).group_by(
            DocumentUpload.id,
            Property.property_code,
            FinancialPeriod.period_year,
            FinancialPeriod.period_month,
            DocumentUpload.extraction_status
        ).all()
        
        # Calculate match rates and filter
        low_match_uploads = []
        for stat in upload_stats:
            if stat.total_records > 0:
                match_rate = (stat.matched_records / stat.total_records) * 100
                if match_rate < 80:  # Re-extract if match rate < 80%
                    low_match_uploads.append({
                        'upload_id': stat.upload_id,
                        'property_code': stat.property_code,
                        'year': stat.period_year,
                        'month': stat.period_month,
                        'total_records': stat.total_records,
                        'matched_records': stat.matched_records,
                        'match_rate': match_rate
                    })
        
        print(f"\n📊 Found {len(low_match_uploads)} cash flow uploads with match rate < 80%")
        
        if not low_match_uploads:
            print("✅ All cash flow documents have acceptable match rates!")
            return
        
        print("\n" + "=" * 80)
        print("UPLOADS TO RE-EXTRACT:")
        print("=" * 80)
        print(f"{'ID':<8} {'Property':<12} {'Period':<12} {'Records':>8} {'Matched':>8} {'Rate':>8}")
        print("-" * 80)
        
        for upload in low_match_uploads[:20]:
            print(f"{upload['upload_id']:<8} {upload['property_code']:<12} {upload['year']}-{upload['month']:02d}      "
                  f"{upload['total_records']:>8} {upload['matched_records']:>8} {upload['match_rate']:>7.1f}%")
        
        if len(low_match_uploads) > 20:
            print(f"... and {len(low_match_uploads) - 20} more uploads")
        
        print("-" * 80)
        
        if dry_run:
            print("\n🔍 DRY RUN MODE - No changes made")
            print(f"   Would re-extract {len(low_match_uploads)} uploads")
            print("\n💡 To execute, run with --execute flag")
        else:
            print(f"\n🚀 EXECUTING: Re-extracting {len(low_match_uploads)} uploads...")
            
            success_count = 0
            error_count = 0
            
            for idx, upload in enumerate(low_match_uploads, 1):
                try:
                    print(f"\n[{idx}/{len(low_match_uploads)}] Re-extracting upload {upload['upload_id']} ({upload['property_code']} {upload['year']}-{upload['month']:02d})...")
                    
                    # Trigger extraction task
                    task = extract_document.delay(upload['upload_id'])
                    print(f"   ✅ Task queued: {task.id}")
                    success_count += 1
                    
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    error_count += 1
            
            print("\n" + "=" * 80)
            print(f"✅ Re-extraction complete:")
            print(f"   - Success: {success_count}")
            print(f"   - Errors: {error_count}")
            print(f"\n💡 Check task status with: celery -A app.core.celery_config inspect active")
            print("=" * 80)
        
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Re-extract low match cash flow documents')
    parser.add_argument('--dry-run', action='store_true', help='Preview without executing')
    parser.add_argument('--execute', action='store_true', help='Execute re-extraction')
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.execute:
        # Default to dry run
        args.dry_run = True
    
    reextract_low_match_cash_flows(dry_run=args.dry_run)

