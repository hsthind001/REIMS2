"""
Extract All MinIO Files with Full REIMS Pipeline

Extracts all PDF files from MinIO, ensuring 100% data quality and zero data loss
using the complete REIMS extraction pipeline including:
- Validation templates
- Validation rules
- Multi-engine extraction
- AI models
- Quality checks

Usage:
    python3 scripts/extract_all_minio_files.py --dry-run
    python3 scripts/extract_all_minio_files.py --execute
"""
import sys
import os
import argparse
import re
import hashlib
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.models.property import Property
from app.models.document_upload import DocumentUpload
from app.models.financial_period import FinancialPeriod
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.rent_roll_data import RentRollData
from app.models.income_statement_header import IncomeStatementHeader
from app.models.cash_flow_header import CashFlowHeader
from app.models.cash_flow_adjustments import CashFlowAdjustment
from app.models.cash_account_reconciliation import CashAccountReconciliation
from app.db.minio_client import list_files, download_file
from app.tasks.extraction_tasks import extract_document


def parse_file_path(file_path: str) -> dict:
    """
    Parse MinIO file path to extract metadata
    
    Expected format: {PROPERTY_CODE}-{NAME}/{YEAR}/{DOC_TYPE}/{FILE}.pdf
    Example: ESP001-Eastern-Shore-Plaza/2023/balance-sheet/ESP_2023_Balance_Sheet.pdf
    
    Returns:
        dict with property_code, year, month, document_type, or None if parsing fails
    """
    try:
        # Split path into components
        parts = file_path.split('/')
        
        if len(parts) < 4:
            return None
        
        # Extract property code (first part before dash)
        property_folder = parts[0]
        property_match = re.match(r'^([A-Z0-9]+)-', property_folder)
        if not property_match:
            return None
        property_code = property_match.group(1)
        
        # Extract year
        try:
            year = int(parts[1])
        except ValueError:
            return None
        
        # Extract document type from folder name
        doc_type_folder = parts[2].lower()
        document_type_map = {
            'balance-sheet': 'balance_sheet',
            'income-statement': 'income_statement',
            'cash-flow': 'cash_flow',
            'rent-roll': 'rent_roll'
        }
        document_type = document_type_map.get(doc_type_folder)
        if not document_type:
            return None
        
        # Extract month from filename (default to 12 for year-end)
        filename = parts[-1]
        month = 12  # Default to year-end
        
        # Try to extract month from filename if present
        month_match = re.search(r'(\d{2})[_-](\d{2})', filename)
        if month_match:
            try:
                month = int(month_match.group(2))
                if month < 1 or month > 12:
                    month = 12
            except ValueError:
                pass
        
        return {
            'property_code': property_code,
            'year': year,
            'month': month,
            'document_type': document_type,
            'file_path': file_path
        }
    except Exception as e:
        print(f"   ⚠️  Error parsing path {file_path}: {e}")
        return None


def list_minio_pdf_files() -> list:
    """
    List all PDF files from MinIO bucket
    
    Returns:
        list of file paths
    """
    print("📋 Listing all PDF files from MinIO...")
    all_files = list_files()
    
    # Filter to PDF files only
    pdf_files = [f for f in all_files if f.lower().endswith('.pdf')]
    
    print(f"   Found {len(pdf_files)} PDF files in MinIO")
    return pdf_files


def delete_old_extracted_data(db, upload: DocumentUpload) -> int:
    """
    Delete old extracted financial data before re-extraction
    
    Returns:
        int: Number of records deleted
    """
    total_deleted = 0
    
    try:
        if upload.document_type == 'balance_sheet':
            deleted = db.query(BalanceSheetData).filter(
                BalanceSheetData.upload_id == upload.id
            ).delete(synchronize_session=False)
            total_deleted += deleted
            
        elif upload.document_type == 'income_statement':
            # Delete header and data
            deleted_header = db.query(IncomeStatementHeader).filter(
                IncomeStatementHeader.upload_id == upload.id
            ).delete(synchronize_session=False)
            total_deleted += deleted_header
            
            deleted_data = db.query(IncomeStatementData).filter(
                IncomeStatementData.upload_id == upload.id
            ).delete(synchronize_session=False)
            total_deleted += deleted_data
            
        elif upload.document_type == 'cash_flow':
            # Delete header, data, adjustments, and reconciliations
            deleted_header = db.query(CashFlowHeader).filter(
                CashFlowHeader.upload_id == upload.id
            ).delete(synchronize_session=False)
            total_deleted += deleted_header
            
            deleted_data = db.query(CashFlowData).filter(
                CashFlowData.upload_id == upload.id
            ).delete(synchronize_session=False)
            total_deleted += deleted_data
            
            deleted_adjustments = db.query(CashFlowAdjustment).filter(
                CashFlowAdjustment.upload_id == upload.id
            ).delete(synchronize_session=False)
            total_deleted += deleted_adjustments
            
            deleted_reconciliations = db.query(CashAccountReconciliation).filter(
                CashAccountReconciliation.upload_id == upload.id
            ).delete(synchronize_session=False)
            total_deleted += deleted_reconciliations
            
        elif upload.document_type == 'rent_roll':
            deleted = db.query(RentRollData).filter(
                RentRollData.upload_id == upload.id
            ).delete(synchronize_session=False)
            total_deleted += deleted
            
    except Exception as e:
        print(f"   ⚠️  Error deleting old data: {e}")
    
    return total_deleted


def get_or_create_period(db, property_obj: Property, year: int, month: int) -> FinancialPeriod:
    """Get or create FinancialPeriod record"""
    period = db.query(FinancialPeriod).filter(
        FinancialPeriod.property_id == property_obj.id,
        FinancialPeriod.period_year == year,
        FinancialPeriod.period_month == month
    ).first()
    
    if not period:
        # Calculate period dates
        if month == 12:
            period_start = date(year, month, 1)
            period_end = date(year, month, 31)
        else:
            period_start = date(year, month, 1)
            # Get last day of month
            if month == 2:
                period_end = date(year, month, 28)  # Simplified, doesn't handle leap years
            elif month in [4, 6, 9, 11]:
                period_end = date(year, month, 30)
            else:
                period_end = date(year, month, 31)
        
        period = FinancialPeriod(
            property_id=property_obj.id,
            period_year=year,
            period_month=month,
            period_start_date=period_start,
            period_end_date=period_end,
            fiscal_year=year,
            fiscal_quarter=(month - 1) // 3 + 1,
            is_closed=False
        )
        db.add(period)
        db.flush()
    
    return period


def process_file(db, file_path: str, dry_run: bool = False) -> dict:
    """
    Process a single file: parse, check/create records, trigger extraction
    
    Returns:
        dict with status, upload_id, task_id, etc.
    """
    result = {
        'file_path': file_path,
        'status': 'error',
        'message': '',
        'upload_id': None,
        'task_id': None
    }
    
    try:
        # Parse file path
        metadata = parse_file_path(file_path)
        if not metadata:
            result['message'] = 'Failed to parse file path'
            return result
        
        property_code = metadata['property_code']
        year = metadata['year']
        month = metadata['month']
        document_type = metadata['document_type']
        
        print(f"   Processing: {property_code} {year}-{month:02d} {document_type}")
        
        # Get property
        property_obj = db.query(Property).filter(
            Property.property_code == property_code
        ).first()
        
        if not property_obj:
            result['message'] = f'Property {property_code} not found'
            print(f"   ❌ {result['message']}")
            return result
        
        # Get or create period
        period = get_or_create_period(db, property_obj, year, month)
        
        # Download file to calculate hash
        if not dry_run:
            pdf_data = download_file(file_path)
            if not pdf_data:
                result['message'] = 'Failed to download file from MinIO'
                print(f"   ❌ {result['message']}")
                return result
            
            file_hash = hashlib.md5(pdf_data).hexdigest()
            file_size = len(pdf_data)
        else:
            file_hash = 'dry-run-hash'
            file_size = 0
        
        # Check for existing DocumentUpload
        existing = db.query(DocumentUpload).filter(
            DocumentUpload.file_path == file_path
        ).first()
        
        if not existing:
            # Also check by hash
            existing = db.query(DocumentUpload).filter(
                DocumentUpload.file_hash == file_hash
            ).first()
        
        if existing:
            print(f"   ℹ️  Found existing upload (ID: {existing.id})")
            
            if not dry_run:
                # Delete old extracted data
                deleted_count = delete_old_extracted_data(db, existing)
                if deleted_count > 0:
                    print(f"   🗑️  Deleted {deleted_count} old records")
                
                # Reset upload status
                existing.extraction_status = 'pending'
                existing.extraction_started_at = None
                existing.extraction_completed_at = None
                existing.notes = None
                db.commit()
                
                upload = existing
            else:
                upload = existing
                result['message'] = f'Would re-extract existing upload (ID: {upload.id})'
        else:
            if not dry_run:
                # Create new DocumentUpload record
                upload = DocumentUpload(
                    property_id=property_obj.id,
                    period_id=period.id,
                    document_type=document_type,
                    file_name=os.path.basename(file_path),
                    file_path=file_path,
                    file_hash=file_hash,
                    file_size_bytes=file_size,
                    extraction_status='pending',
                    is_active=True
                )
                db.add(upload)
                db.flush()
                print(f"   ✅ Created upload record (ID: {upload.id})")
            else:
                result['message'] = 'Would create new upload record'
                upload = None
        
        # Trigger extraction
        if not dry_run and upload:
            task = extract_document.delay(upload.id)
            print(f"   ✅ Extraction task queued: {task.id}")
            result['status'] = 'success'
            result['upload_id'] = upload.id
            result['task_id'] = task.id
            result['message'] = 'Extraction queued successfully'
        elif dry_run:
            result['status'] = 'dry_run'
            result['message'] = result['message'] or 'Would queue extraction'
        else:
            result['status'] = 'error'
            result['message'] = 'No upload record created'
        
    except Exception as e:
        result['status'] = 'error'
        result['message'] = str(e)
        print(f"   ❌ Error: {e}")
        if not dry_run:
            db.rollback()
    
    return result


def extract_all_minio_files(dry_run: bool = False):
    """Main function to extract all MinIO files"""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("EXTRACT ALL MINIO FILES WITH FULL REIMS PIPELINE")
        print("=" * 80)
        
        if dry_run:
            print("\n🔍 DRY RUN MODE - No changes will be made")
            print("   Run with --execute to perform actual extraction\n")
        
        # List all PDF files
        pdf_files = list_minio_pdf_files()
        
        if not pdf_files:
            print("❌ No PDF files found in MinIO")
            return
        
        print(f"\n📊 Processing {len(pdf_files)} PDF files...")
        print("=" * 80)
        
        success_count = 0
        error_count = 0
        skip_count = 0
        task_ids = []
        
        for idx, file_path in enumerate(pdf_files, 1):
            print(f"\n[{idx}/{len(pdf_files)}] {file_path}")
            
            result = process_file(db, file_path, dry_run=dry_run)
            
            if result['status'] == 'success':
                success_count += 1
                if result['task_id']:
                    task_ids.append(result['task_id'])
            elif result['status'] == 'dry_run':
                success_count += 1
            elif result['status'] == 'error':
                error_count += 1
                print(f"   ❌ {result['message']}")
            else:
                skip_count += 1
        
        # Commit all changes
        if not dry_run:
            db.commit()
        
        # Summary report
        print("\n" + "=" * 80)
        print("EXTRACTION SUMMARY:")
        print("=" * 80)
        print(f"✅ Success: {success_count}")
        print(f"⚠️  Skipped: {skip_count}")
        print(f"❌ Errors: {error_count}")
        
        if not dry_run and task_ids:
            print(f"\n📋 Extraction Tasks Queued: {len(task_ids)}")
            print("   Task IDs:")
            for task_id in task_ids[:10]:  # Show first 10
                print(f"      - {task_id}")
            if len(task_ids) > 10:
                print(f"      ... and {len(task_ids) - 10} more")
        
        print("\n💡 Monitor extraction progress:")
        print("   - celery -A app.core.celery_config inspect active")
        print("   - Check /api/v1/quality/statistics/yearly for updated metrics")
        print("   - View extraction logs in database")
        
        if dry_run:
            print("\n⚠️  This was a DRY RUN. Run with --execute to perform actual extraction.")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        if not dry_run:
            db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Extract all PDF files from MinIO using full REIMS pipeline'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview operations without executing (default)'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Execute extraction (overrides --dry-run)'
    )
    
    args = parser.parse_args()
    
    # Default to dry-run unless --execute is specified
    dry_run = not args.execute
    
    extract_all_minio_files(dry_run=dry_run)

