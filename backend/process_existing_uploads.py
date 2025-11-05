#!/usr/bin/env python3
"""
Process existing Cash Flow upload records (IDs 2-8)
"""
import sys
sys.path.insert(0, '/home/gurpyar/Documents/R/REIMS2/backend')

from app.db.database import SessionLocal
from app.utils.financial_table_parser import FinancialTableParser
from app.services.extraction_orchestrator import ExtractionOrchestrator
from app.models.document_upload import DocumentUpload
from app.models.cash_flow_header import CashFlowHeader
from app.models.cash_flow_data import CashFlowData

# Map upload IDs to PDF files
PDF_MAPPING = {
    2: "/home/gurpyar/REIMS_Uploaded/ESP 2023 Cash Flow Statement.pdf",
    3: "/home/gurpyar/REIMS_Uploaded/Hammond Aire 2023 Cash Flow Statement.pdf",
    4: "/home/gurpyar/REIMS_Uploaded/Hammond Aire 2024 Cash Flow Statement.pdf",
    5: "/home/gurpyar/REIMS_Uploaded/TCSH 2023 Cash FLow Statement.pdf",
    6: "/home/gurpyar/REIMS_Uploaded/TCSH 2024 Cash Flow Statement.pdf",
    7: "/home/gurpyar/REIMS_Uploaded/Wendover Commons 2023 Cash Flow Statement.pdf",
    8: "/home/gurpyar/REIMS_Uploaded/Wendover Commons 2024 Cash Flow Statement.pdf",
}

def process_uploads():
    """Process upload records 2-8"""
    db = SessionLocal()
    parser = FinancialTableParser()
    orchestrator = ExtractionOrchestrator(db)
    
    results = []
    
    print("🚀 PROCESSING 7 CASH FLOW STATEMENTS")
    print("=" * 100)
    print()
    
    for upload_id, pdf_path in PDF_MAPPING.items():
        upload = db.query(DocumentUpload).filter(DocumentUpload.id == upload_id).first()
        
        if not upload:
            print(f"❌ Upload {upload_id} not found")
            continue
        
        file_name = upload.file_name
        print(f"📄 [{upload_id}/8] {file_name}")
        print("-" * 100)
        
        try:
            # Check if already extracted
            existing_header = db.query(CashFlowHeader).filter(
                CashFlowHeader.property_id == upload.property_id,
                CashFlowHeader.period_id == upload.period_id
            ).first()
            
            if existing_header and upload.extraction_status == 'completed':
                print(f"  ⏭️  Already extracted")
                item_count = db.query(CashFlowData).filter(
                    CashFlowData.header_id == existing_header.id
                ).count()
                
                print(f"  📊 Line Items: {item_count}")
                print(f"  💰 NOI: ${existing_header.net_operating_income:,.2f}")
                
                results.append({
                    "upload_id": upload_id,
                    "file": file_name,
                    "success": True,
                    "items": item_count,
                    "status": "already_done"
                })
                print()
                continue
            
            # Extract from PDF
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()
            
            print(f"  🔄 Parsing PDF...")
            parsed_data = parser.extract_cash_flow_table(pdf_data)
            
            if not parsed_data.get('success'):
                print(f"  ❌ Parsing failed")
                results.append({
                    "upload_id": upload_id,
                    "file": file_name,
                    "success": False,
                    "error": "parsing_failed"
                })
                print()
                continue
            
            print(f"  ✅ Parsed: {parsed_data['total_items']} line items")
            
            # Insert data
            print(f"  💾 Inserting...")
            records = orchestrator._insert_cash_flow_data(upload, parsed_data, 95.0)
            
            # Update upload status
            upload.extraction_status = 'completed'
            db.commit()
            
            print(f"  ✅ Inserted: {records} records")
            
            # Get stats
            header = db.query(CashFlowHeader).filter(
                CashFlowHeader.property_id == upload.property_id,
                CashFlowHeader.period_id == upload.period_id
            ).first()
            
            if header:
                print(f"  📊 NOI: ${header.net_operating_income:,.2f}")
                print(f"  💰 Net Income: ${header.net_income:,.2f}")
                print(f"  💵 Cash Flow: ${header.cash_flow:,.2f}")
                
                results.append({
                    "upload_id": upload_id,
                    "file": file_name,
                    "success": True,
                    "items": records,
                    "noi": float(header.net_operating_income),
                    "status": "newly_extracted"
                })
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            db.rollback()
            results.append({
                "upload_id": upload_id,
                "file": file_name,
                "success": False,
                "error": str(e)
            })
        
        print()
    
    # Summary
    print("=" * 100)
    print("📊 FINAL SUMMARY")
    print("=" * 100)
    print()
    
    successful = [r for r in results if r.get('success')]
    print(f"✅ Successfully Processed: {len(successful)}/7")
    print()
    
    if successful:
        newly_done = [r for r in successful if r.get('status') == 'newly_extracted']
        already_done = [r for r in successful if r.get('status') == 'already_done']
        
        print(f"  🆕 Newly Extracted: {len(newly_done)}")
        print(f"  ✅ Already Done: {len(already_done)}")
        
        if newly_done:
            total = sum(r['items'] for r in newly_done)
            print(f"  📊 New Records: {total:,}")
        print()
    
    # Final counts
    header_count = db.query(CashFlowHeader).count()
    item_count = db.query(CashFlowData).filter(CashFlowData.header_id.isnot(None)).count()
    
    print(f"🗄️  TOTAL IN DATABASE:")
    print(f"  • Cash Flow Headers: {header_count}")
    print(f"  • Cash Flow Line Items: {item_count:,}")
    print()
    
    print("=" * 100)
    print("✅ PROCESSING COMPLETE")
    print("=" * 100)
    
    db.close()

if __name__ == "__main__":
    process_uploads()

