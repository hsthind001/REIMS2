"""
PDF Extraction Analysis Tool

Diagnoses why extraction is producing low line item counts.
Shows what's being filtered out and why.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pdfplumber
import io
from typing import Dict, List
from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.db.minio_client import download_file
from app.core.config import settings
from app.utils.financial_table_parser import FinancialTableParser

# Colors
CYAN = '\033[96m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
END = '\033[0m'


def analyze_pdf(upload_id: int) -> Dict:
    """Analyze a single PDF in detail"""
    db = SessionLocal()
    
    try:
        upload = db.query(DocumentUpload).filter(DocumentUpload.id == upload_id).first()
        if not upload:
            return {"error": f"Upload {upload_id} not found"}
        
        print(f"\n{CYAN}{BOLD}{'='*80}{END}")
        print(f"{CYAN}{BOLD}Analyzing: {upload.file_name}{END}")
        print(f"{CYAN}{BOLD}{'='*80}{END}\n")
        
        # Download PDF
        pdf_data = download_file(upload.file_path, settings.MINIO_BUCKET_NAME)
        if not pdf_data:
            return {"error": "Failed to download PDF"}
        
        # Basic PDF info
        pdf = pdfplumber.open(io.BytesIO(pdf_data))
        print(f"{BOLD}PDF Information:{END}")
        print(f"  Pages: {len(pdf.pages)}")
        print(f"  Document type: {upload.document_type}")
        print(f"  File size: {len(pdf_data)} bytes")
        
        # Check if scanned
        first_page_text = pdf.pages[0].extract_text()
        is_scanned = len(first_page_text.strip()) < 50 if first_page_text else True
        print(f"  Is scanned (image-based): {RED + 'YES - NEEDS OCR' + END if is_scanned else GREEN + 'NO - Digital text' + END}")
        
        # Analyze each page
        all_raw_items = []
        all_tables_found = []
        
        for page_num, page in enumerate(pdf.pages, 1):
            print(f"\n{BOLD}Page {page_num}:{END}")
            
            # Text extraction
            text = page.extract_text()
            if text:
                lines = [l for l in text.split('\n') if l.strip()]
                print(f"  Text lines: {len(lines)}")
                print(f"  Characters: {len(text)}")
            else:
                print(f"  {RED}No text extracted - likely scanned{END}")
            
            # Table detection
            tables = page.extract_tables()
            print(f"  Tables detected: {len(tables)}")
            
            if tables:
                for i, table in enumerate(tables):
                    print(f"    Table {i+1}: {len(table)} rows, {len(table[0]) if table else 0} columns")
                    all_tables_found.append({
                        'page': page_num,
                        'table_num': i+1,
                        'rows': len(table),
                        'cols': len(table[0]) if table else 0,
                        'data': table
                    })
        
        pdf.close()
        
        # Now run extraction with detailed logging
        print(f"\n{BOLD}Running Table Extraction:{END}")
        parser = FinancialTableParser()
        
        if upload.document_type == "balance_sheet":
            result = parser.extract_balance_sheet_table(pdf_data)
        elif upload.document_type == "income_statement":
            result = parser.extract_income_statement_table(pdf_data)
        elif upload.document_type == "cash_flow":
            result = parser.extract_cash_flow_table(pdf_data)
        elif upload.document_type == "rent_roll":
            result = parser.extract_rent_roll_table(pdf_data)
        else:
            result = {"success": False, "error": "Unknown document type"}
        
        print(f"  Success: {result.get('success')}")
        print(f"  Extraction method: {result.get('extraction_method', 'unknown')}")
        print(f"  Line items extracted: {BOLD}{result.get('total_items', 0)}{END}")
        
        if result.get('line_items'):
            print(f"\n{BOLD}Extracted Line Items:{END}")
            for i, item in enumerate(result['line_items'][:20], 1):
                code = item.get('account_code', '')
                name = item.get('account_name', '')
                amount = item.get('amount', item.get('period_amount', item.get('monthly_rent', 0)))
                conf = item.get('confidence', 0)
                
                print(f"  {i:2d}. {code:12s} {name:40s} ${amount:>12,.2f} ({conf:.0f}%)")
            
            if len(result['line_items']) > 20:
                print(f"  ... and {len(result['line_items']) - 20} more items")
        
        # Show raw table data for first table
        if all_tables_found:
            print(f"\n{BOLD}Raw Table Data (First Table):{END}")
            first_table = all_tables_found[0]['data']
            for i, row in enumerate(first_table[:15]):
                row_str = ' | '.join([str(cell)[:30] if cell else '' for cell in row])
                print(f"  Row {i:2d}: {row_str}")
            
            if len(first_table) > 15:
                print(f"  ... and {len(first_table) - 15} more rows")
        
        # Analysis summary
        print(f"\n{BOLD}Analysis Summary:{END}")
        if is_scanned:
            print(f"  {RED}⚠ PDF is scanned - needs OCR support{END}")
        
        if not all_tables_found:
            print(f"  {RED}⚠ No tables detected - using text fallback{END}")
        
        if result.get('total_items', 0) < 10:
            print(f"  {RED}⚠ Very few items extracted - likely filtering too aggressively{END}")
            print(f"    Possible causes:")
            print(f"    - Header detection too strict")
            print(f"    - Account code pattern doesn't match")
            print(f"    - Amount parsing failures")
            print(f"    - Table structure not recognized")
        
        return {
            "success": True,
            "upload_id": upload_id,
            "file_name": upload.file_name,
            "pages": len(pdf.pages) if 'pdf' in locals() else 0,
            "is_scanned": is_scanned,
            "tables_found": len(all_tables_found),
            "items_extracted": result.get('total_items', 0)
        }
    
    finally:
        db.close()


def analyze_all_financials():
    """Analyze all financial statement PDFs"""
    db = SessionLocal()
    
    try:
        uploads = db.query(DocumentUpload).filter(
            DocumentUpload.document_type.in_(['balance_sheet', 'income_statement', 'cash_flow'])
        ).order_by(DocumentUpload.id).all()
        
        print(f"\n{CYAN}{BOLD}{'='*80}{END}")
        print(f"{CYAN}{BOLD}PDF Extraction Analysis - All Financial Statements{END}")
        print(f"{CYAN}{BOLD}{'='*80}{END}")
        print(f"\nAnalyzing {len(uploads)} financial documents...\n")
        
        results = []
        for upload in uploads:
            result = analyze_pdf(upload.id)
            if result.get('success'):
                results.append(result)
        
        # Summary table
        print(f"\n{CYAN}{BOLD}{'='*80}{END}")
        print(f"{CYAN}{BOLD}Summary{END}")
        print(f"{CYAN}{BOLD}{'='*80}{END}\n")
        
        print(f"{'ID':<4} {'Type':<17} {'Scanned':<8} {'Tables':<7} {'Items':<6} {'File Name'}")
        print(f"{'-'*4} {'-'*17} {'-'*8} {'-'*7} {'-'*6} {'-'*40}")
        
        for r in results:
            scanned_str = 'YES' if r['is_scanned'] else 'NO'
            color = RED if r['items_extracted'] < 10 else GREEN if r['items_extracted'] > 30 else YELLOW
            
            print(f"{r['upload_id']:<4} {r['file_name'][:17]:<17} {scanned_str:<8} {r['tables_found']:<7} {color}{r['items_extracted']:<6}{END} {r['file_name']}")
        
        # Statistics
        total_items = sum(r['items_extracted'] for r in results)
        avg_items = total_items / len(results) if results else 0
        scanned_count = sum(1 for r in results if r['is_scanned'])
        
        print(f"\n{BOLD}Statistics:{END}")
        print(f"  Total documents: {len(results)}")
        print(f"  Scanned PDFs: {scanned_count} ({scanned_count/len(results)*100:.0f}%)")
        print(f"  Total items extracted: {total_items}")
        print(f"  Average items per document: {avg_items:.1f}")
        print(f"  Documents with <10 items: {sum(1 for r in results if r['items_extracted'] < 10)}")
        
    finally:
        db.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze PDF extraction quality')
    parser.add_argument('--upload-id', type=int, help='Analyze specific upload ID')
    parser.add_argument('--all', action='store_true', help='Analyze all financial statements')
    
    args = parser.parse_args()
    
    if args.upload_id:
        analyze_pdf(args.upload_id)
    elif args.all:
        analyze_all_financials()
    else:
        print("Usage:")
        print("  python3 scripts/analyze_pdf_extraction.py --upload-id 1")
        print("  python3 scripts/analyze_pdf_extraction.py --all")


if __name__ == "__main__":
    main()

