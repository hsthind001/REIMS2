"""
Test Extraction Improvements

Test extraction on sample PDFs to validate improvements before full re-extraction.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pdfplumber
import io
from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.db.minio_client import download_file
from app.core.config import settings
from app.utils.financial_table_parser import FinancialTableParser

# Colors
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
CYAN = '\033[96m'
BOLD = '\033[1m'
END = '\033[0m'


def test_extraction():
    """Test extraction on sample documents"""
    
    print(f"\n{CYAN}{BOLD}{'='*80}{END}")
    print(f"{CYAN}{BOLD}Testing Extraction Improvements{END}")
    print(f"{CYAN}{BOLD}{'='*80}{END}\n")
    
    db = SessionLocal()
    
    # Test targets: 3 documents (one of each type)
    test_cases = [
        {"id": 1, "type": "balance_sheet", "target": 40, "file": "ESP 2023 Balance Sheet.pdf"},
        {"id": 3, "type": "income_statement", "target": 30, "file": "ESP 2023 Income Statement.pdf"},
        {"id": 2, "type": "cash_flow", "target": 20, "file": "ESP 2023 Cash Flow Statement.pdf"},
    ]
    
    results = []
    
    for test in test_cases:
        print(f"{BOLD}Testing: {test['file']}{END}")
        print(f"  Type: {test['type']}")
        print(f"  Target: >{test['target']} items")
        
        # Get upload
        upload = db.query(DocumentUpload).filter(DocumentUpload.id == test['id']).first()
        if not upload:
            print(f"  {RED}✗ Upload not found{END}\n")
            continue
        
        # Download PDF
        pdf_data = download_file(upload.file_path, settings.MINIO_BUCKET_NAME)
        if not pdf_data:
            print(f"  {RED}✗ Failed to download{END}\n")
            continue
        
        # Run extraction
        parser = FinancialTableParser()
        
        if test['type'] == 'balance_sheet':
            result = parser.extract_balance_sheet_table(pdf_data)
        elif test['type'] == 'income_statement':
            result = parser.extract_income_statement_table(pdf_data)
        elif test['type'] == 'cash_flow':
            result = parser.extract_cash_flow_table(pdf_data)
        else:
            print(f"  {RED}✗ Unknown type{END}\n")
            continue
        
        items_extracted = result.get('total_items', 0)
        success = result.get('success', False)
        method = result.get('extraction_method', 'unknown')
        
        # Evaluate
        passed = items_extracted >= test['target']
        status_color = GREEN if passed else RED
        status_icon = "✓" if passed else "✗"
        
        print(f"  Method: {method}")
        print(f"  Items extracted: {items_extracted}")
        print(f"  {status_color}{status_icon} {'PASS' if passed else 'FAIL'} (target: {test['target']}){END}\n")
        
        results.append({
            'file': test['file'],
            'type': test['type'],
            'target': test['target'],
            'extracted': items_extracted,
            'passed': passed
        })
    
    db.close()
    
    # Summary
    print(f"{CYAN}{BOLD}{'='*80}{END}")
    print(f"{CYAN}{BOLD}Test Results Summary{END}")
    print(f"{CYAN}{BOLD}{'='*80}{END}\n")
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['passed'])
    
    print(f"{'Document Type':<20} {'Target':>8} {'Extracted':>10} {'Result':>8}")
    print(f"{'-'*20} {'-'*8} {'-'*10} {'-'*8}")
    
    for r in results:
        color = GREEN if r['passed'] else RED
        result_str = "PASS" if r['passed'] else "FAIL"
        print(f"{r['type']:<20} {r['target']:>8} {color}{r['extracted']:>10}{END} {color}{result_str:>8}{END}")
    
    print()
    print(f"{BOLD}Total: {passed_tests}/{total_tests} tests passed{END}")
    
    if passed_tests == total_tests:
        print(f"\n{GREEN}{BOLD}✓ All tests passed! Ready to re-extract all documents.{END}\n")
        return True
    else:
        print(f"\n{RED}{BOLD}✗ Some tests failed. Review extraction logic before proceeding.{END}\n")
        return False


if __name__ == "__main__":
    success = test_extraction()
    sys.exit(0 if success else 1)

