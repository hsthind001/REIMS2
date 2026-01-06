#!/usr/bin/env python3
"""
Test Single Mortgage Statement Extraction

Attempts to extract a single mortgage statement with detailed error reporting
to identify the root cause of the transaction failures.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.db.minio_client import download_file


def test_single_mortgage():
    """Test extraction of a single mortgage statement with detailed logging"""

    print("=" * 80)
    print("Test Single Mortgage Statement Extraction")
    print("=" * 80)
    print()

    session = SessionLocal()

    try:
        # Get first mortgage statement upload
        upload = session.query(DocumentUpload).filter(
            DocumentUpload.document_type == 'mortgage_statement'
        ).first()

        if not upload:
            print("❌ No mortgage statement uploads found")
            return

        print(f"📄 Testing Upload ID: {upload.id}")
        print(f"   File: {upload.file_name}")
        print(f"   Property ID: {upload.property_id}")
        print(f"   Period ID: {upload.period_id}")
        print()

        # Download PDF
        print("📥 Downloading PDF...")
        pdf_data = download_file(
            object_name=upload.file_path,
            bucket_name=settings.MINIO_BUCKET_NAME
        )

        if not pdf_data:
            print("❌ Failed to download PDF")
            return

        print(f"✅ Downloaded {len(pdf_data):,} bytes")
        print()

        # Extract text
        print("🔍 Extracting text from PDF...")
        from app.utils.extraction_engine import MultiEngineExtractor

        extractor = MultiEngineExtractor()
        extraction_result = extractor.extract(
            pdf_data=pdf_data,
            document_type='mortgage_statement'
        )

        extracted_text = extraction_result.get("extraction", {}).get("text", "")
        print(f"✅ Extracted {len(extracted_text)} characters")
        print()

        # Extract mortgage data
        print("📋 Extracting mortgage data...")
        from app.services.mortgage_extraction_service import MortgageExtractionService

        mortgage_service = MortgageExtractionService(session)
        mortgage_result = mortgage_service.extract_mortgage_data(
            extracted_text=extracted_text,
            pdf_data=pdf_data
        )

        print(f"Success: {mortgage_result.get('success')}")
        if mortgage_result.get('success'):
            mortgage_data = mortgage_result.get('mortgage_data', {})
            print(f"Extracted fields: {list(mortgage_data.keys())}")
            print()
            print("Key fields:")
            print(f"  loan_number: {mortgage_data.get('loan_number')}")
            print(f"  statement_date: {mortgage_data.get('statement_date')}")
            print(f"  principal_balance: {mortgage_data.get('principal_balance')}")
            print(f"  lender_id: {mortgage_data.get('lender_id')}")
            print()
        else:
            print(f"Error: {mortgage_result.get('error')}")
            print()

        # Try to insert the data
        print("💾 Attempting to insert into database...")
        print()

        from app.services.extraction_orchestrator import ExtractionOrchestrator

        orchestrator = ExtractionOrchestrator(session)

        try:
            parsed_data = {
                "success": mortgage_result.get("success"),
                "mortgage_data": mortgage_result.get("mortgage_data", {}),
                "extraction_coordinates": mortgage_result.get("extraction_coordinates", {}),
                "extraction_method": mortgage_result.get("extraction_method", "template_patterns"),
                "confidence": mortgage_result.get("confidence", 50.0)
            }

            records = orchestrator._insert_mortgage_statement_data(
                upload=upload,
                parsed_data=parsed_data,
                confidence_score=mortgage_result.get("confidence", 50.0)
            )

            print(f"✅ Successfully inserted {records} record(s)")
            print()

        except Exception as insert_error:
            print(f"❌ Insertion failed: {insert_error}")
            print()
            import traceback
            traceback.print_exc()
            session.rollback()

    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    test_single_mortgage()
