#!/usr/bin/env python3
"""
Test Mortgage Extraction for ESP001 Wells Fargo Statements
Tests extraction on all 11 PDFs from MinIO and identifies gaps
"""

import sys
import os
from io import BytesIO
from decimal import Decimal

# Add backend to path
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.document_upload import DocumentUpload
from app.models.mortgage_statement_data import MortgageStatementData
from app.services.mortgage_extraction_service import MortgageExtractionService
from app.core.config import settings
import boto3


def get_minio_client():
    """Get MinIO S3 client"""
    return boto3.client(
        's3',
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_access_key_id=settings.MINIO_ROOT_USER,
        aws_secret_access_key=settings.MINIO_ROOT_PASSWORD,
        region_name='us-east-1'
    )


def download_pdf_from_minio(pdf_key: str) -> bytes:
    """Download PDF from MinIO"""
    s3_client = get_minio_client()
    response = s3_client.get_object(Bucket=settings.MINIO_BUCKET_NAME, Key=pdf_key)
    return response['Body'].read()


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF using pdfplumber"""
    import pdfplumber

    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"
        return full_text


def test_single_mortgage_extraction(pdf_key: str, period_month: int):
    """Test extraction on a single mortgage PDF"""
    db = SessionLocal()

    try:
        print(f"\n{'='*80}")
        print(f"Testing: {pdf_key}")
        print(f"Period: {period_month:02d}/2023")
        print(f"{'='*80}")

        # Download PDF
        print("\n[1/5] Downloading PDF from MinIO...")
        pdf_bytes = download_pdf_from_minio(pdf_key)
        print(f"✓ Downloaded {len(pdf_bytes)} bytes")

        # Extract text
        print("\n[2/5] Extracting text from PDF...")
        pdf_text = extract_text_from_pdf(pdf_bytes)
        print(f"✓ Extracted {len(pdf_text)} characters")

        # Show first 500 chars as sample
        print(f"\n  Sample text (first 500 chars):")
        print(f"  {pdf_text[:500]}")

        # Initialize extraction service
        print("\n[3/5] Running mortgage extraction...")
        extraction_service = MortgageExtractionService(db)
        result = extraction_service.extract_mortgage_data(pdf_text, pdf_bytes)

        # Show results
        print(f"\n[4/5] Extraction Results:")
        print(f"  Success: {result.get('success')}")
        print(f"  Confidence: {result.get('confidence', 0):.2f}%")
        print(f"  Extraction Method: {result.get('extraction_method')}")

        if result.get('error'):
            print(f"  ✗ Error: {result['error']}")

        # Show extracted fields
        mortgage_data = result.get('mortgage_data', {})
        print(f"\n  Extracted Fields ({len(mortgage_data)} total):")

        # Group fields by category
        categories = {
            'Identification': ['loan_number', 'lender_id', 'loan_type', 'borrower_name', 'property_address'],
            'Dates': ['statement_date', 'payment_due_date', 'maturity_date', 'origination_date'],
            'Balances': ['principal_balance', 'tax_escrow_balance', 'insurance_escrow_balance',
                        'reserve_balance', 'other_escrow_balance', 'suspense_balance', 'total_loan_balance'],
            'Payment Due': ['principal_due', 'interest_due', 'tax_escrow_due', 'insurance_escrow_due',
                           'reserve_due', 'late_fees', 'other_fees', 'total_payment_due'],
            'YTD': ['ytd_principal_paid', 'ytd_interest_paid', 'ytd_taxes_disbursed',
                   'ytd_insurance_disbursed', 'ytd_reserve_disbursed', 'ytd_total_paid'],
            'Loan Terms': ['interest_rate', 'original_loan_amount', 'loan_term_months',
                          'payment_frequency', 'amortization_type'],
            'Calculated': ['remaining_term_months', 'annual_debt_service', 'monthly_debt_service', 'ltv_ratio']
        }

        for category, fields in categories.items():
            print(f"\n  {category}:")
            for field in fields:
                value = mortgage_data.get(field)
                status = "✓" if value is not None else "✗"
                if value is not None:
                    if isinstance(value, Decimal):
                        print(f"    {status} {field}: ${value:,.2f}")
                    else:
                        print(f"    {status} {field}: {value}")
                else:
                    print(f"    {status} {field}: MISSING")

        # Calculate extraction completeness
        print(f"\n[5/5] Data Quality Analysis:")
        total_fields = sum(len(fields) for fields in categories.values())
        extracted_fields = sum(1 for field in mortgage_data.values() if field is not None)
        completeness = (extracted_fields / total_fields) * 100

        print(f"  Total Fields Expected: {total_fields}")
        print(f"  Fields Extracted: {extracted_fields}")
        print(f"  Completeness: {completeness:.1f}%")

        if completeness < 80:
            print(f"\n  ⚠️  WARNING: Completeness below 80% - missing critical fields")
        elif completeness < 100:
            print(f"\n  ⚠️  WARNING: Some optional fields missing")
        else:
            print(f"\n  ✅ SUCCESS: 100% field extraction")

        return {
            'pdf_key': pdf_key,
            'period_month': period_month,
            'success': result.get('success'),
            'confidence': result.get('confidence', 0),
            'completeness': completeness,
            'extracted_fields': extracted_fields,
            'total_fields': total_fields,
            'mortgage_data': mortgage_data
        }

    except Exception as e:
        print(f"\n✗ EXTRACTION FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'pdf_key': pdf_key,
            'period_month': period_month,
            'success': False,
            'error': str(e)
        }
    finally:
        db.close()


def main():
    """Test all mortgage PDFs"""

    # Map PDFs to periods (based on filename pattern ESP_2023_MM_Mortgage_Statement.pdf)
    mortgage_pdfs = [
        ('ESP001-Eastern-Shore-Plaza/2023/mortgage-statement/ESP_2023_01_Mortgage_Statement.pdf', 1),
        ('ESP001-Eastern-Shore-Plaza/2023/mortgage-statement/ESP_2023_02_Mortgage_Statement.pdf', 2),
        ('ESP001-Eastern-Shore-Plaza/2023/mortgage-statement/ESP_2023_03_Mortgage_Statement.pdf', 3),
        ('ESP001-Eastern-Shore-Plaza/2023/mortgage-statement/ESP_2023_04_Mortgage_Statement.pdf', 4),
        ('ESP001-Eastern-Shore-Plaza/2023/mortgage-statement/ESP_2023_05_Mortgage_Statement.pdf', 5),
        ('ESP001-Eastern-Shore-Plaza/2023/mortgage-statement/ESP_2023_06_Mortgage_Statement.pdf', 6),
        ('ESP001-Eastern-Shore-Plaza/2023/mortgage-statement/ESP_2023_07_Mortgage_Statement.pdf', 7),
        ('ESP001-Eastern-Shore-Plaza/2023/mortgage-statement/ESP_2023_08_Mortgage_Statement.pdf', 8),
        ('ESP001-Eastern-Shore-Plaza/2023/mortgage-statement/ESP_2023_09_Mortgage_Statement.pdf', 9),
        ('ESP001-Eastern-Shore-Plaza/2023/mortgage-statement/ESP_2023_10_Mortgage_Statement.pdf', 10),
        ('ESP001-Eastern-Shore-Plaza/2023/mortgage-statement/ESP_2023_11_Mortgage_Statement.pdf', 11),
    ]

    print("\n" + "="*80)
    print("MORTGAGE EXTRACTION TEST - ESP001 Wells Fargo Statements 2023")
    print("="*80)

    results = []
    for pdf_key, period_month in mortgage_pdfs:
        result = test_single_mortgage_extraction(pdf_key, period_month)
        results.append(result)

    # Summary Report
    print("\n\n" + "="*80)
    print("SUMMARY REPORT")
    print("="*80)

    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]

    print(f"\nTotal PDFs Tested: {len(results)}")
    print(f"Successful Extractions: {len(successful)}")
    print(f"Failed Extractions: {len(failed)}")

    if successful:
        avg_confidence = sum(r['confidence'] for r in successful) / len(successful)
        avg_completeness = sum(r['completeness'] for r in successful) / len(successful)

        print(f"\nAverage Confidence: {avg_confidence:.2f}%")
        print(f"Average Completeness: {avg_completeness:.2f}%")

        print(f"\nDetailed Results:")
        for r in results:
            status = "✓" if r.get('success') else "✗"
            month = r['period_month']
            confidence = r.get('confidence', 0)
            completeness = r.get('completeness', 0)
            print(f"  {status} Month {month:02d}/2023: Confidence={confidence:.1f}% Completeness={completeness:.1f}%")

    # Identify missing fields across all extractions
    print(f"\n\nFIELD EXTRACTION ANALYSIS:")
    print("=" * 80)

    # Count how many times each field was extracted
    field_counts = {}
    for r in successful:
        for field, value in r.get('mortgage_data', {}).items():
            if field not in field_counts:
                field_counts[field] = 0
            if value is not None:
                field_counts[field] += 1

    # Sort by extraction success rate
    sorted_fields = sorted(field_counts.items(), key=lambda x: x[1], reverse=True)

    print(f"\nField Extraction Success Rate (out of {len(successful)} successful extractions):")
    for field, count in sorted_fields:
        success_rate = (count / len(successful)) * 100 if successful else 0
        status = "✓" if success_rate == 100 else "⚠" if success_rate >= 50 else "✗"
        print(f"  {status} {field:35s}: {count}/{len(successful)} ({success_rate:.0f}%)")

    # Identify consistently missing fields
    missing_fields = [field for field, count in sorted_fields if count == 0]
    if missing_fields:
        print(f"\n⚠️  CRITICAL: These fields were NEVER extracted:")
        for field in missing_fields:
            print(f"    ✗ {field}")


if __name__ == "__main__":
    main()
