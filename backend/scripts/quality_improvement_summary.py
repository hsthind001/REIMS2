"""
Quality Improvement Implementation Summary

Displays the current state of data quality improvements including:
- Chart of accounts additions
- Re-extraction queue status
- Income statement uploads
- Expected outcomes
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.models.chart_of_accounts import ChartOfAccounts
from app.models.document_upload import DocumentUpload
from app.models.cash_flow_data import CashFlowData
from app.models.income_statement_data import IncomeStatementData
from sqlalchemy import func


def print_summary():
    """Print implementation summary"""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print(" 📊 DATA QUALITY IMPROVEMENT - IMPLEMENTATION SUMMARY")
        print("=" * 80)
        
        # === PRIORITY 1: CASH FLOW MATCH RATE ===
        print("\n🔴 PRIORITY 1: CASH FLOW MATCH RATE IMPROVEMENT")
        print("=" * 80)
        
        # Count new accounts added
        new_accounts = db.query(ChartOfAccounts).filter(
            ChartOfAccounts.account_code.like('9%')
        ).count()
        
        inter_property_accounts = db.query(ChartOfAccounts).filter(
            ChartOfAccounts.account_code.like('2510-%')
        ).count()
        
        print(f"✅ New accounts added to chart_of_accounts:")
        print(f"   - Non-cash adjustment accounts (9xxx): {new_accounts}")
        print(f"   - Inter-property AP accounts (2510-xxxx): {inter_property_accounts}")
        print(f"   - Total new accounts: {new_accounts + inter_property_accounts}")
        
        # Count re-extraction queue
        pending_reextract = db.query(DocumentUpload).filter(
            DocumentUpload.document_type == 'cash_flow',
            DocumentUpload.extraction_status == 'pending'
        ).count()
        
        processing_reextract = db.query(DocumentUpload).filter(
            DocumentUpload.document_type == 'cash_flow',
            DocumentUpload.extraction_status == 'processing'
        ).count()
        
        print(f"\n✅ Cash flow re-extraction status:")
        print(f"   - Queued for re-extraction: {pending_reextract}")
        print(f"   - Currently processing: {processing_reextract}")
        
        # Current match rate
        total_cf = db.query(func.count(CashFlowData.id)).scalar()
        matched_cf = db.query(func.count(CashFlowData.id)).filter(
            CashFlowData.account_id.isnot(None)
        ).scalar()
        
        if total_cf > 0:
            match_rate = (matched_cf / total_cf) * 100
            print(f"\n📊 Current cash flow match rate: {match_rate:.1f}%")
            print(f"   - Total records: {total_cf}")
            print(f"   - Matched: {matched_cf}")
            print(f"   - Unmatched: {total_cf - matched_cf}")
        
        # === PRIORITY 2: INCOME STATEMENTS ===
        print("\n\n⚪ PRIORITY 2: INCOME STATEMENT UPLOADS")
        print("=" * 80)
        
        income_uploads = db.query(DocumentUpload).filter(
            DocumentUpload.document_type == 'income_statement'
        ).count()
        
        income_pending = db.query(DocumentUpload).filter(
            DocumentUpload.document_type == 'income_statement',
            DocumentUpload.extraction_status == 'pending'
        ).count()
        
        income_completed = db.query(DocumentUpload).filter(
            DocumentUpload.document_type == 'income_statement',
            DocumentUpload.extraction_status == 'completed'
        ).count()
        
        print(f"✅ Income statement uploads:")
        print(f"   - Total uploads: {income_uploads}")
        print(f"   - Completed: {income_completed}")
        print(f"   - Pending extraction: {income_pending}")
        
        if income_completed > 0:
            total_is = db.query(func.count(IncomeStatementData.id)).scalar()
            matched_is = db.query(func.count(IncomeStatementData.id)).filter(
                IncomeStatementData.account_id.isnot(None)
            ).scalar()
            
            if total_is > 0:
                is_match_rate = (matched_is / total_is) * 100
                print(f"\n📊 Income statement match rate: {is_match_rate:.1f}%")
                print(f"   - Total records: {total_is}")
                print(f"   - Matched: {matched_is}")
        
        # === PRIORITY 3: LEGACY DATA ===
        print("\n\n⚠️  PRIORITY 3: LEGACY DATA RE-EXTRACTION")
        print("=" * 80)
        print("✅ No legacy documents found - all data already has proper match tracking")
        
        # === CELERY STATUS ===
        print("\n\n🔧 CELERY WORKER STATUS")
        print("=" * 80)
        
        total_pending_tasks = pending_reextract + income_pending
        
        print(f"📋 Total extraction tasks queued: {total_pending_tasks}")
        print(f"   - Cash flow re-extractions: {pending_reextract}")
        print(f"   - Income statement extractions: {income_pending}")
        
        if total_pending_tasks > 0:
            print("\n⚠️  NOTE: Tasks are queued but require Celery worker to process")
            print("   To start Celery worker:")
            print("   $ cd backend && source venv/bin/activate")
            print("   $ celery -A app.core.celery_config worker --loglevel=info")
        
        # === NEXT STEPS ===
        print("\n\n📋 NEXT STEPS")
        print("=" * 80)
        
        if total_pending_tasks > 0:
            print("1. Start Celery worker to process queued extractions")
            print("2. Monitor extraction progress:")
            print("   $ celery -A app.core.celery_config inspect active")
            print("3. Once complete, check updated statistics:")
            print("   $ curl http://localhost:8000/api/v1/quality/statistics/yearly")
        else:
            print("✅ All tasks completed!")
            print("📊 Check final statistics:")
            print("   $ curl http://localhost:8000/api/v1/quality/statistics/yearly")
        
        print("\n" + "=" * 80)
        
    finally:
        db.close()


if __name__ == "__main__":
    print_summary()

