#!/usr/bin/env python3
import sys
sys.path.insert(0, '/app')

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.services.extraction_service import ExtractionService
from app.services.mortgage_extraction_service import MortgageExtractionService

db = SessionLocal()

try:
    upload_id = 408  # 2023.08.06 esp wells fargo loan 1008.pdf

    upload = db.query(DocumentUpload).filter(DocumentUpload.id == upload_id).first()
    if not upload:
        print(f'Upload {upload_id} not found')
        sys.exit(1)

    print(f'Testing extraction for: {upload.file_name}')

    from app.services.storage_service import StorageService
    storage = StorageService()

    pdf_data = storage.get_file(upload.minio_path)
    print(f'Retrieved PDF from MinIO ({len(pdf_data)} bytes)')

    extraction_service = ExtractionService()
    text_result = extraction_service.extract_text_from_pdf(pdf_data)
    extracted_text = text_result.get('text', '')
    print(f'Extracted text ({len(extracted_text)} characters)')

    mortgage_service = MortgageExtractionService(db)
    result = mortgage_service.extract_mortgage_data(extracted_text, pdf_data)

    print(f'\nExtraction Result:')
    print(f'  Success: {result.get("success")}')
    print(f'  Confidence: {result.get("confidence", 0):.1f}%')

    if result.get('success'):
        mortgage_data = result.get('mortgage_data', {})
        print(f'\nExtracted Fields:')
        print(f'  Loan Number: {mortgage_data.get("loan_number")}')
        print(f'  Statement Date: {mortgage_data.get("statement_date")}')
        print(f'  Principal Balance: ${mortgage_data.get("principal_balance", 0):,.2f}')
        print(f'  YTD Principal Paid: ${mortgage_data.get("ytd_principal_paid", 0):,.2f}')
        print(f'  YTD Interest Paid: ${mortgage_data.get("ytd_interest_paid", 0):,.2f}')
        print(f'  Total Payment Due: ${mortgage_data.get("total_payment_due", 0):,.2f}')
        print(f'  Principal Due: ${mortgage_data.get("principal_due", 0):,.2f}')
        print(f'  Interest Due: ${mortgage_data.get("interest_due", 0):,.2f}')
        print(f'  Tax Escrow Due: ${mortgage_data.get("tax_escrow_due", 0):,.2f}')
        print(f'  Insurance Escrow Due: ${mortgage_data.get("insurance_escrow_due", 0):,.2f}')
        print(f'  Reserve Due: ${mortgage_data.get("reserve_due", 0):,.2f}')
    else:
        print(f'  Error: {result.get("error", "Unknown")}')

except Exception as e:
    import traceback
    print(f'Error: {str(e)}')
    traceback.print_exc()
finally:
    db.close()
