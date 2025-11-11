"""
Upload Income Statement Documents from MinIO

Uploads income statement PDFs that already exist in MinIO but haven't been
processed through the document upload system.

Usage:
    python3 scripts/upload_income_statements_from_minio.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.models.property import Property
from app.models.document_upload import DocumentUpload
from app.services.document_service import DocumentService
from app.db.minio_client import download_file, get_file_info
from app.tasks.extraction_tasks import extract_document
import hashlib


def upload_income_statements():
    """Upload income statement documents from MinIO"""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("UPLOAD INCOME STATEMENTS FROM MINIO")
        print("=" * 80)
        
        # Define income statement files to upload
        income_statements = [
            {'property': 'ESP001', 'year': 2023, 'month': 12, 'path': 'ESP001-Eastern-Shore-Plaza/2023/income-statement/ESP_2023_Income_Statement.pdf'},
            {'property': 'ESP001', 'year': 2024, 'month': 12, 'path': 'ESP001-Eastern-Shore-Plaza/2024/income-statement/ESP_2024_Income_Statement.pdf'},
            {'property': 'HMND001', 'year': 2023, 'month': 12, 'path': 'HMND001-Hammond-Aire/2023/income-statement/HMND_2023_Income_Statement.pdf'},
            {'property': 'HMND001', 'year': 2024, 'month': 12, 'path': 'HMND001-Hammond-Aire/2024/income-statement/HMND_2024_Income_Statement.pdf'},
            {'property': 'TCSH001', 'year': 2023, 'month': 12, 'path': 'TCSH001-The-Crossings/2023/income-statement/TCSH_2023_Income_Statement.pdf'},
            {'property': 'TCSH001', 'year': 2024, 'month': 12, 'path': 'TCSH001-The-Crossings/2024/income-statement/TCSH_2024_Income_Statement.pdf'},
            {'property': 'WEND001', 'year': 2023, 'month': 12, 'path': 'WEND001-Wendover-Commons/2023/income-statement/WEND_2023_Income_Statement.pdf'},
            {'property': 'WEND001', 'year': 2024, 'month': 12, 'path': 'WEND001-Wendover-Commons/2024/income-statement/WEND_2024_Income_Statement.pdf'},
        ]
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for idx, doc in enumerate(income_statements, 1):
            print(f"\n[{idx}/{len(income_statements)}] Processing {doc['property']} {doc['year']}-{doc['month']:02d}...")
            
            try:
                # Get property
                property_obj = db.query(Property).filter(
                    Property.property_code == doc['property']
                ).first()
                
                if not property_obj:
                    print(f"   ❌ Property {doc['property']} not found")
                    error_count += 1
                    continue
                
                # Get or create period
                from app.models.financial_period import FinancialPeriod
                from datetime import date
                
                period = db.query(FinancialPeriod).filter(
                    FinancialPeriod.property_id == property_obj.id,
                    FinancialPeriod.period_year == doc['year'],
                    FinancialPeriod.period_month == doc['month']
                ).first()
                
                if not period:
                    # Create period
                    period = FinancialPeriod(
                        property_id=property_obj.id,
                        period_year=doc['year'],
                        period_month=doc['month'],
                        period_start_date=date(doc['year'], doc['month'], 1),
                        period_end_date=date(doc['year'], doc['month'], 28),  # Simplified
                        fiscal_year=doc['year'],
                        fiscal_quarter=(doc['month'] - 1) // 3 + 1,
                        is_closed=False
                    )
                    db.add(period)
                    db.flush()
                
                # Check if already uploaded
                existing = db.query(DocumentUpload).filter(
                    DocumentUpload.property_id == property_obj.id,
                    DocumentUpload.period_id == period.id,
                    DocumentUpload.document_type == 'income_statement'
                ).first()
                
                if existing:
                    print(f"   ⚠️  Already uploaded (ID: {existing.id})")
                    skip_count += 1
                    continue
                
                # Download from MinIO to get file info
                pdf_data = download_file(doc['path'])
                if not pdf_data:
                    print(f"   ❌ Failed to download from MinIO")
                    error_count += 1
                    continue
                
                # Calculate hash
                file_hash = hashlib.md5(pdf_data).hexdigest()
                file_size = len(pdf_data)
                
                # Create document upload record
                upload = DocumentUpload(
                    property_id=property_obj.id,
                    period_id=period.id,
                    document_type='income_statement',
                    file_name=os.path.basename(doc['path']),
                    file_path=doc['path'],
                    file_hash=file_hash,
                    file_size_bytes=file_size,
                    extraction_status='pending',
                    is_active=True
                )
                db.add(upload)
                db.flush()
                
                print(f"   ✅ Created upload record (ID: {upload.id})")
                
                # Trigger extraction
                task = extract_document.delay(upload.id)
                print(f"   ✅ Extraction task queued: {task.id}")
                
                success_count += 1
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                error_count += 1
        
        db.commit()
        
        print("\n" + "=" * 80)
        print("UPLOAD COMPLETE:")
        print("=" * 80)
        print(f"✅ Success: {success_count}")
        print(f"⚠️  Skipped (already exists): {skip_count}")
        print(f"❌ Errors: {error_count}")
        print(f"\n💡 Total income statements queued for extraction: {success_count}")
        print("=" * 80)
        
    finally:
        db.close()


if __name__ == "__main__":
    upload_income_statements()

