#!/usr/bin/env python3
"""
Test all 8 Cash Flow PDFs - Upload, Extract, Validate, and Report
"""
import sys
sys.path.insert(0, '/home/gurpyar/Documents/R/REIMS2/backend')

from app.db.database import SessionLocal
from app.services.document_service import DocumentService
from app.services.extraction_orchestrator import ExtractionOrchestrator
from app.services.validation_service import ValidationService
from app.models.cash_flow_header import CashFlowHeader
from app.models.cash_flow_data import CashFlowData

# All Cash Flow PDFs to test
TEST_FILES = [
    ("ESP001", 2023, 12, "/home/gurpyar/REIMS_Uploaded/ESP 2023 Cash Flow Statement.pdf"),
    ("ESP001", 2024, 12, "/home/gurpyar/REIMS_Uploaded/ESP 2024 Cash Flow Statement.pdf"),
    ("HMND001", 2023, 12, "/home/gurpyar/REIMS_Uploaded/Hammond Aire 2023 Cash Flow Statement.pdf"),
    ("HMND001", 2024, 12, "/home/gurpyar/REIMS_Uploaded/Hammond Aire 2024 Cash Flow Statement.pdf"),
    ("TCSH001", 2023, 12, "/home/gurpyar/REIMS_Uploaded/TCSH 2023 Cash FLow Statement.pdf"),
    ("TCSH001", 2024, 12, "/home/gurpyar/REIMS_Uploaded/TCSH 2024 Cash Flow Statement.pdf"),
    ("WEND001", 2023, 12, "/home/gurpyar/REIMS_Uploaded/Wendover Commons 2023 Cash Flow Statement.pdf"),
    ("WEND001", 2024, 12, "/home/gurpyar/REIMS_Uploaded/Wendover Commons 2024 Cash Flow Statement.pdf"),
]

def test_all_cash_flows():
    """Upload and extract all Cash Flow statements"""
    db = SessionLocal()
    doc_service = DocumentService(db)
    extractor = ExtractionOrchestrator(db)
    validator = ValidationService(db)
    
    results = []
    
    print("🧪 TESTING ALL 8 CASH FLOW STATEMENTS")
    print("=" * 100)
    
    for property_code, year, month, pdf_path in TEST_FILES:
        print(f"\n📄 Processing: {property_code} {year}-{month:02d}")
        print("-" * 100)
        
        try:
            # Upload document
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()
                file_name = pdf_path.split('/')[-1]
                
                upload = doc_service.upload_document(
                    property_code=property_code,
                    period_year=year,
                    period_month=month,
                    document_type="cash_flow",
                    file_data=pdf_data,
                    file_name=file_name
                )
            
            upload_id = upload["upload_id"]
            print(f"  ✅ Uploaded: ID {upload_id}")
            
            # Extract data
            extraction_result = extractor.extract_and_parse_document(upload_id)
            print(f"  ✅ Extracted: {extraction_result.get('records_inserted', 0)} records")
            print(f"  🎯 Confidence: {extraction_result.get('confidence_score', 0):.2f}%")
            
            # Validate
            validation_result = validator.validate_upload(upload_id)
            print(f"  ✅ Validated: {validation_result.get('passed_checks', 0)}/{validation_result.get('total_checks', 0)} checks passed")
            
            # Get header for summary
            header = db.query(CashFlowHeader).filter(
                CashFlowHeader.upload_id == upload_id
            ).first()
            
            result_summary = {
                "property_code": property_code,
                "year": year,
                "month": month,
                "upload_id": upload_id,
                "records": extraction_result.get('records_inserted', 0),
                "confidence": extraction_result.get('confidence_score', 0),
                "validations_passed": validation_result.get('passed_checks', 0),
                "validations_total": validation_result.get('total_checks', 0),
                "noi": float(header.net_operating_income) if header else 0,
                "net_income": float(header.net_income) if header else 0,
                "cash_flow": float(header.cash_flow) if header else 0
            }
            results.append(result_summary)
            
            print(f"  📊 NOI: ${result_summary['noi']:,.2f}")
            print(f"  💰 Net Income: ${result_summary['net_income']:,.2f}")
            print(f"  💵 Cash Flow: ${result_summary['cash_flow']:,.2f}")
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            results.append({
                "property_code": property_code,
                "year": year,
                "month": month,
                "error": str(e)
            })
    
    # Summary
    print("\n" + "=" * 100)
    print("📊 SUMMARY: ALL CASH FLOW STATEMENTS")
    print("=" * 100)
    
    successful = [r for r in results if 'error' not in r]
    failed = [r for r in results if 'error' in r]
    
    print(f"\n✅ Successful: {len(successful)}/{len(TEST_FILES)}")
    print(f"❌ Failed: {len(failed)}/{len(TEST_FILES)}")
    
    if successful:
        print(f"\n📈 EXTRACTION STATISTICS:")
        total_records = sum(r['records'] for r in successful)
        avg_confidence = sum(r['confidence'] for r in successful) / len(successful)
        total_validations = sum(r['validations_passed'] for r in successful)
        
        print(f"  • Total Records Extracted: {total_records}")
        print(f"  • Average Confidence: {avg_confidence:.2f}%")
        print(f"  • Total Validations Passed: {total_validations}")
        
        print(f"\n📋 BY PROPERTY:")
        for r in successful:
            status = "✅" if r['validations_passed'] == r['validations_total'] else "⚠️"
            print(f"  {status} {r['property_code']} {r['year']}-{r['month']:02d}: "
                  f"{r['records']} items, {r['confidence']:.1f}% confidence, "
                  f"NOI: ${r['noi']:,.2f}")
    
    # Database summary
    print(f"\n🗄️  DATABASE SUMMARY:")
    header_count = db.query(CashFlowHeader).count()
    item_count = db.query(CashFlowData).filter(CashFlowData.header_id.isnot(None)).count()
    
    print(f"  • Cash Flow Headers: {header_count}")
    print(f"  • Cash Flow Line Items: {item_count}")
    print(f"  • Average Items per Statement: {item_count/header_count if header_count > 0 else 0:.0f}")
    
    print("\n" + "=" * 100)
    print("✅ TESTING COMPLETE")
    print("=" * 100)
    
    db.close()
    return results

if __name__ == "__main__":
    test_all_cash_flows()

