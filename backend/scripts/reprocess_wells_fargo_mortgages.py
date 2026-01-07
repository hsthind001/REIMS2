"""
Re-process Wells Fargo mortgage statements with fixed extraction service
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.core.config import settings
from app.models.document_upload import DocumentUpload
from app.models.mortgage_statement_data import MortgageStatementData
from app.services.mortgage_extraction_service import MortgageExtractionService
from app.utils.engines.pdfplumber_engine import PDFPlumberEngine
from minio import Minio
from datetime import datetime

# Create DB session
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Initialize MinIO client
minio_client = Minio(
    'minio:9000',
    access_key='minioadmin',
    secret_key='minioadmin',
    secure=False
)

def reprocess_mortgage_uploads():
    """Re-process all Wells Fargo mortgage statement uploads"""

    print("=" * 80)
    print("🔄 Re-processing Wells Fargo Mortgage Statements")
    print("=" * 80)

    # Get all completed mortgage uploads (not failed)
    uploads = db.query(DocumentUpload).filter(
        DocumentUpload.document_type == 'mortgage_statement',
        DocumentUpload.extraction_status == 'completed'
    ).order_by(DocumentUpload.id).all()

    print(f"\n📄 Found {len(uploads)} mortgage uploads to process\n")

    # Delete existing mortgage records for these uploads
    print("🗑️  Deleting existing mortgage records...")
    for upload in uploads:
        existing_count = db.query(MortgageStatementData).filter(
            MortgageStatementData.property_id == upload.property_id,
            MortgageStatementData.period_id == upload.period_id
        ).delete()
        if existing_count > 0:
            print(f"  • Deleted {existing_count} existing records for Upload ID {upload.id}")
    db.commit()

    # Process each upload
    pdf_engine = PDFPlumberEngine()
    mortgage_service = MortgageExtractionService(db)

    success_count = 0
    failure_count = 0

    for upload in uploads:
        print(f"\n📄 Processing Upload ID {upload.id}: {upload.file_name}")
        print(f"   Property ID: {upload.property_id}, Period ID: {upload.period_id}")
        print(f"   File Path: {upload.file_path}")

        try:
            # Download PDF from MinIO
            response = minio_client.get_object('reims', upload.file_path)
            pdf_bytes = response.read()
            response.close()
            response.release_conn()

            print(f"   ✅ Downloaded PDF ({len(pdf_bytes)} bytes)")

            # Extract text
            pdf_result = pdf_engine.extract(pdf_bytes)
            if not pdf_result.success:
                print(f"   ❌ Text extraction failed")
                failure_count += 1
                continue

            text = pdf_result.extracted_data['text']
            print(f"   ✅ Extracted text ({len(text)} chars)")

            # Extract mortgage data
            mortgage_result = mortgage_service.extract_mortgage_data(text, pdf_bytes)

            if mortgage_result.get('success'):
                mortgage_data = mortgage_result.get('mortgage_data', {})
                confidence = mortgage_result.get('confidence', 0)

                print(f"   ✅ Mortgage extraction successful (confidence: {confidence:.1f}%)")
                print(f"      • Loan Number: {mortgage_data.get('loan_number')}")
                print(f"      • Statement Date: {mortgage_data.get('statement_date')}")
                print(f"      • Principal Balance: ${mortgage_data.get('principal_balance', 0):,.2f}")
                print(f"      • Total Payment Due: ${mortgage_data.get('total_payment_due', 0):,.2f}")

                # Insert into database
                new_record = MortgageStatementData(
                    property_id=upload.property_id,
                    period_id=upload.period_id,
                    upload_id=upload.id,
                    lender_id=mortgage_data.get('lender_id'),

                    # Required fields
                    loan_number=str(mortgage_data.get('loan_number')),
                    statement_date=mortgage_data.get('statement_date'),

                    # Balances
                    principal_balance=mortgage_data.get('principal_balance'),
                    tax_escrow_balance=mortgage_data.get('tax_escrow_balance'),
                    insurance_escrow_balance=mortgage_data.get('insurance_escrow_balance'),
                    reserve_balance=mortgage_data.get('reserve_balance'),
                    other_escrow_balance=mortgage_data.get('other_escrow_balance'),
                    suspense_balance=mortgage_data.get('suspense_balance'),
                    total_loan_balance=mortgage_data.get('total_loan_balance'),

                    # Payment Information
                    payment_due_date=mortgage_data.get('payment_due_date'),
                    principal_due=mortgage_data.get('principal_due'),
                    interest_due=mortgage_data.get('interest_due'),
                    tax_escrow_due=mortgage_data.get('tax_escrow_due'),
                    insurance_escrow_due=mortgage_data.get('insurance_escrow_due'),
                    reserve_due=mortgage_data.get('reserve_due'),
                    late_fees=mortgage_data.get('late_fees'),
                    other_fees=mortgage_data.get('other_fees'),
                    total_payment_due=mortgage_data.get('total_payment_due'),

                    # Loan Details
                    interest_rate=mortgage_data.get('interest_rate'),
                    maturity_date=mortgage_data.get('maturity_date'),
                    remaining_term_months=mortgage_data.get('remaining_term_months'),

                    # Year-to-Date
                    ytd_principal_paid=mortgage_data.get('ytd_principal_paid'),
                    ytd_interest_paid=mortgage_data.get('ytd_interest_paid'),
                    ytd_taxes_disbursed=mortgage_data.get('ytd_taxes_disbursed'),
                    ytd_insurance_disbursed=mortgage_data.get('ytd_insurance_disbursed'),
                    ytd_reserve_disbursed=mortgage_data.get('ytd_reserve_disbursed'),
                    ytd_total_paid=mortgage_data.get('ytd_total_paid'),

                    # Calculated Metrics
                    monthly_debt_service=mortgage_data.get('monthly_debt_service'),
                    annual_debt_service=mortgage_data.get('annual_debt_service'),

                    # Metadata
                    extraction_confidence=confidence
                )

                db.add(new_record)
                db.commit()

                print(f"   ✅ Inserted mortgage record (ID: {new_record.id})")
                success_count += 1

            else:
                error = mortgage_result.get('error', 'Unknown error')
                print(f"   ❌ Mortgage extraction failed: {error}")
                failure_count += 1

        except Exception as e:
            print(f"   ❌ Error processing upload: {e}")
            import traceback
            traceback.print_exc()
            failure_count += 1
            db.rollback()

    print("\n" + "=" * 80)
    print(f"📊 Processing Complete:")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Failed: {failure_count}")
    print(f"   📄 Total: {len(uploads)}")
    print("=" * 80)

    db.close()

if __name__ == "__main__":
    reprocess_mortgage_uploads()
