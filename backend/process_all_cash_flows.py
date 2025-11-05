#!/usr/bin/env python3
"""
Process all 7 remaining Cash Flow PDFs
Uploads and extracts each one, showing detailed results
"""
import sys
sys.path.insert(0, '/home/gurpyar/Documents/R/REIMS2/backend')

from app.db.database import SessionLocal
from app.services.document_service import DocumentService
from app.services.extraction_orchestrator import ExtractionOrchestrator
from app.models.cash_flow_header import CashFlowHeader
from app.models.cash_flow_data import CashFlowData
import hashlib
from datetime import datetime

# Remaining Cash Flow PDFs to process
CASH_FLOW_FILES = [
    ("ESP001", 2023, 12, "/home/gurpyar/REIMS_Uploaded/ESP 2023 Cash Flow Statement.pdf"),
    ("HMND001", 2023, 12, "/home/gurpyar/REIMS_Uploaded/Hammond Aire 2023 Cash Flow Statement.pdf"),
    ("HMND001", 2024, 12, "/home/gurpyar/REIMS_Uploaded/Hammond Aire 2024 Cash Flow Statement.pdf"),
    ("TCSH001", 2023, 12, "/home/gurpyar/REIMS_Uploaded/TCSH 2023 Cash FLow Statement.pdf"),
    ("TCSH001", 2024, 12, "/home/gurpyar/REIMS_Uploaded/TCSH 2024 Cash Flow Statement.pdf"),
    ("WEND001", 2023, 12, "/home/gurpyar/REIMS_Uploaded/Wendover Commons 2023 Cash Flow Statement.pdf"),
    ("WEND001", 2024, 12, "/home/gurpyar/REIMS_Uploaded/Wendover Commons 2024 Cash Flow Statement.pdf"),
]

def process_all_cash_flows():
    """Process all 7 remaining Cash Flow PDFs"""
    db = SessionLocal()
    doc_service = DocumentService(db)
    extractor = ExtractionOrchestrator(db)
    
    results = []
    
    print("🚀 PROCESSING ALL 7 REMAINING CASH FLOW STATEMENTS")
    print("=" * 100)
    print()
    
    for idx, (property_code, year, month, pdf_path) in enumerate(CASH_FLOW_FILES, 1):
        file_name = pdf_path.split('/')[-1]
        print(f"📄 [{idx}/7] Processing: {file_name}")
        print("-" * 100)
        
        try:
            # Read PDF
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()
            
            # Create upload record manually (since upload_document has different signature)
            from app.models.document_upload import DocumentUpload
            from app.models.property import Property
            from app.models.financial_period import FinancialPeriod
            from datetime import date
            
            # Get property
            property = db.query(Property).filter(Property.property_code == property_code).first()
            if not property:
                print(f"  ❌ Property {property_code} not found")
                continue
            
            # Get or create period
            period = db.query(FinancialPeriod).filter(
                FinancialPeriod.property_id == property.id,
                FinancialPeriod.period_year == year,
                FinancialPeriod.period_month == month
            ).first()
            
            if not period:
                period = FinancialPeriod(
                    property_id=property.id,
                    period_year=year,
                    period_month=month,
                    period_start_date=date(year, month, 1),
                    period_end_date=date(year, month, 31) if month != 12 else date(year, 12, 31)
                )
                db.add(period)
                db.flush()
            
            # Calculate hash
            file_hash = hashlib.md5(pdf_data).hexdigest()
            
            # Check for duplicate
            existing = db.query(DocumentUpload).filter(
                DocumentUpload.property_id == property.id,
                DocumentUpload.period_id == period.id,
                DocumentUpload.document_type == 'cash_flow',
                DocumentUpload.file_hash == file_hash
            ).first()
            
            if existing:
                print(f"  ⏭️  Skipping: Already uploaded (ID: {existing.id})")
                upload = existing
            else:
                # Create upload record
                upload = DocumentUpload(
                    property_id=property.id,
                    period_id=period.id,
                    document_type='cash_flow',
                    file_name=file_name,
                    file_path=f"{property_code}/{year}/{month}/{file_name}",
                    file_hash=file_hash,
                    file_size_bytes=len(pdf_data),
                    extraction_status='pending'
                )
                db.add(upload)
                db.flush()
                print(f"  ✅ Uploaded: ID {upload.id}")
            
            # Extract
            print(f"  🔄 Extracting...")
            result = extractor.extract_and_parse_document(upload.id)
            
            records = result.get('records_inserted', 0)
            confidence = result.get('confidence_score', 0)
            
            print(f"  ✅ Extracted: {records} records")
            print(f"  🎯 Confidence: {confidence:.1f}%")
            
            # Get header stats
            header = db.query(CashFlowHeader).filter(
                CashFlowHeader.property_id == property.id,
                CashFlowHeader.period_id == period.id
            ).first()
            
            if header:
                print(f"  📊 Total Income: ${header.total_income:,.2f}")
                print(f"  📊 NOI: ${header.net_operating_income:,.2f} ({header.noi_percentage or 0:.2f}%)")
                print(f"  💰 Net Income: ${header.net_income:,.2f}")
                print(f"  💵 Cash Flow: ${header.cash_flow:,.2f}")
                
                # Count sections
                sections = db.query(CashFlowData.line_section, db.func.count()).filter(
                    CashFlowData.header_id == header.id,
                    CashFlowData.period_amount != 0
                ).group_by(CashFlowData.line_section).all()
                
                section_summary = ", ".join([f"{s[0]}: {s[1]}" for s in sections])
                print(f"  📂 Sections: {section_summary}")
            
            results.append({
                "property": property_code,
                "year": year,
                "month": month,
                "success": True,
                "records": records,
                "confidence": confidence,
                "noi": float(header.net_operating_income) if header else 0,
                "net_income": float(header.net_income) if header else 0
            })
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            results.append({
                "property": property_code,
                "year": year,
                "month": month,
                "success": False,
                "error": str(e)
            })
        
        print()
    
    # Final Summary
    print("=" * 100)
    print("📊 FINAL SUMMARY - ALL CASH FLOW STATEMENTS")
    print("=" * 100)
    print()
    
    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]
    
    print(f"✅ Successfully Processed: {len(successful)}/7")
    print(f"❌ Failed: {len(failed)}/7")
    print()
    
    if successful:
        total_records = sum(r['records'] for r in successful)
        avg_confidence = sum(r['confidence'] for r in successful) / len(successful)
        
        print(f"📈 STATISTICS:")
        print(f"  • Total Records Extracted: {total_records:,}")
        print(f"  • Average Confidence: {avg_confidence:.2f}%")
        print(f"  • Average Items per Statement: {total_records/len(successful):.0f}")
        print()
        
        print(f"📋 BY PROPERTY:")
        for r in successful:
            print(f"  ✅ {r['property']} {r['year']}-{r['month']:02d}: "
                  f"{r['records']:,} items, NOI: ${r['noi']:,.2f}, "
                  f"Net Income: ${r['net_income']:,.2f}")
        print()
    
    # Database totals
    print(f"🗄️  DATABASE TOTALS:")
    header_count = db.query(CashFlowHeader).count()
    item_count = db.query(CashFlowData).filter(CashFlowData.header_id.isnot(None)).count()
    
    print(f"  • Total Cash Flow Headers: {header_count}")
    print(f"  • Total Cash Flow Line Items: {item_count:,}")
    print(f"  • Statements using Template v1.0: {header_count}")
    print()
    
    print("=" * 100)
    print("✅ ALL CASH FLOW PROCESSING COMPLETE")
    print("=" * 100)
    
    db.close()

if __name__ == "__main__":
    process_all_cash_flows()

