#!/usr/bin/env python3
"""
Manual Cash Flow extraction and insertion
Demonstrates complete workflow without Celery
"""
import sys
sys.path.insert(0, '/home/gurpyar/Documents/R/REIMS2/backend')

from app.db.database import SessionLocal
from app.services.extraction_orchestrator import ExtractionOrchestrator
from app.models.document_upload import DocumentUpload
from app.models.cash_flow_header import CashFlowHeader
from app.models.cash_flow_data import CashFlowData
from app.models.cash_flow_adjustments import CashFlowAdjustment
from app.models.cash_account_reconciliation import CashAccountReconciliation

def process_pending_cash_flow_uploads():
    """Process all pending cash flow uploads"""
    db = SessionLocal()
    
    try:
        # Find pending cash flow uploads
        pending_uploads = db.query(DocumentUpload).filter(
            DocumentUpload.document_type == 'cash_flow',
            DocumentUpload.extraction_status == 'pending'
        ).all()
        
        print(f"Found {len(pending_uploads)} pending Cash Flow uploads")
        print("=" * 80)
        
        for upload in pending_uploads:
            print(f"\n📄 Processing Upload ID: {upload.id}")
            print(f"  Property: {upload.property_id}")
            print(f"  Period: {upload.period_id}")
            print(f"  File: {upload.file_name}")
            
            # Create orchestrator
            orchestrator = ExtractionOrchestrator(db)
            
            # Process extraction
            print("  🔄 Extracting data...")
            result = orchestrator.extract_and_parse_document(upload.id)
            
            print(f"  ✅ Extraction: {result.get('status', 'unknown')}")
            print(f"  📊 Records inserted: {result.get('records_inserted', 0)}")
            print(f"  🎯 Confidence: {result.get('confidence_score', 0):.2f}%")
            
        # Show results
        print("\n" + "=" * 80)
        print("📊 EXTRACTION RESULTS:")
        print("=" * 80)
        
        # Count headers
        header_count = db.query(CashFlowHeader).count()
        print(f"✅ Cash Flow Headers: {header_count}")
        
        # Count line items with template fields
        template_items = db.query(CashFlowData).filter(
            CashFlowData.header_id.isnot(None)
        ).count()
        print(f"✅ Line Items (Template v1.0): {template_items}")
        
        # Count adjustments
        adjustment_count = db.query(CashFlowAdjustment).count()
        print(f"✅ Adjustments: {adjustment_count}")
        
        # Count cash accounts
        cash_account_count = db.query(CashAccountReconciliation).count()
        print(f"✅ Cash Account Reconciliations: {cash_account_count}")
        
        # Show details of extracted headers
        if header_count > 0:
            print("\n📋 EXTRACTED HEADERS:")
            headers = db.query(CashFlowHeader).all()
            for h in headers:
                print(f"\n  Property: {h.property_code}")
                print(f"  Period: {h.report_period_start} to {h.report_period_end}")
                print(f"  Total Income: ${h.total_income:,.2f}")
                print(f"  Total Expenses: ${h.total_expenses:,.2f}")
                print(f"  NOI: ${h.net_operating_income:,.2f} ({h.noi_percentage}%)")
                print(f"  Net Income: ${h.net_income:,.2f}")
                print(f"  Cash Flow: ${h.cash_flow:,.2f} ({h.cash_flow_percentage}%)")
                print(f"  Confidence: {h.extraction_confidence}%")
        
        # Show sample line items
        if template_items > 0:
            print("\n📝 SAMPLE LINE ITEMS:")
            sample_items = db.query(CashFlowData).filter(
                CashFlowData.header_id.isnot(None)
            ).order_by(CashFlowData.line_number).limit(10).all()
            
            for item in sample_items:
                section = item.line_section or 'N/A'
                subcategory = item.line_subcategory or item.account_name
                amount = item.period_amount
                flags = ""
                if item.is_total:
                    flags = " [TOTAL]"
                elif item.is_subtotal:
                    flags = " [SUBTOTAL]"
                print(f"  {section} > {subcategory}: ${amount:,.2f}{flags}")
        
        print("\n" + "=" * 80)
        print("✅ MANUAL EXTRACTION COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    process_pending_cash_flow_uploads()

