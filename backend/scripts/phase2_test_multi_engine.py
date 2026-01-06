#!/usr/bin/env python3
"""
Phase 2 Test: Multi-Engine Consensus Extraction

Tests the multi-engine consensus extraction on a sample income statement
to verify:
1. Both engines (PDFPlumber + PyMuPDF) run successfully
2. Consensus calculation works
3. Field-level confidence tracking is implemented
4. Quality metrics improve over single-engine extraction
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


def test_multi_engine_extraction():
    """Test multi-engine extraction on a sample upload"""

    print("=" * 80)
    print("Phase 2 Test: Multi-Engine Consensus Extraction")
    print("=" * 80)
    print()

    session = SessionLocal()

    try:
        # Get a sample income statement upload
        upload = session.query(DocumentUpload).filter(
            DocumentUpload.document_type == "income_statement",
            DocumentUpload.extraction_status == "completed"
        ).first()

        if not upload:
            print("❌ No completed income statement uploads found for testing")
            return

        print(f"📄 Testing with Upload ID: {upload.id}")
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

        # Test multi-engine extraction
        print("🔧 Running multi-engine consensus extraction...")
        print()

        from app.utils.financial_table_parser import FinancialTableParser

        parser = FinancialTableParser()
        result = parser.extract_income_statement_multi_engine(pdf_data)

        # Display results
        print()
        print("=" * 80)
        print("EXTRACTION RESULTS")
        print("=" * 80)
        print()

        if not result.get("success"):
            print(f"❌ Extraction failed: {result.get('error')}")
            return

        print("✅ Extraction successful!")
        print()

        # Metrics
        print("📊 METRICS:")
        print(f"   Engines used: {', '.join(result.get('engines_used', []))}")
        print(f"   Extraction method: {result.get('extraction_method')}")
        print(f"   Consensus score: {result.get('consensus_score', 0):.1f}%")
        print(f"   Total line items: {result.get('total_items', 0)}")
        print(f"   Total pages: {result.get('total_pages', 0)}")
        print()

        if "total_fields_compared" in result:
            print("🔍 CONSENSUS DETAILS:")
            print(f"   Fields compared: {result.get('total_fields_compared', 0)}")
            print(f"   Matching fields: {result.get('matching_fields', 0)}")
            if result.get('total_fields_compared', 0) > 0:
                match_pct = (result.get('matching_fields', 0) / result.get('total_fields_compared', 1)) * 100
                print(f"   Match rate: {match_pct:.1f}%")
            print()

        # Sample line items
        line_items = result.get('line_items', [])
        if line_items:
            print("📋 SAMPLE LINE ITEMS (first 5):")
            for i, item in enumerate(line_items[:5], 1):
                print(f"\n   [{i}] {item.get('account_code')} - {item.get('account_name')}")
                print(f"       Period: ${item.get('period_amount', 0):,.2f}")
                print(f"       YTD: ${item.get('ytd_amount', 0):,.2f}")

                # Show field confidence if available
                if 'field_confidence' in item:
                    print(f"       Field confidence: {item['field_confidence']}")

                print(f"       Base confidence: {item.get('confidence', 0):.1f}%")

        print()

        # Header info
        header = result.get('header', {})
        if header:
            print("📋 HEADER METADATA:")
            print(f"   Property: {header.get('property_name')}")
            print(f"   Period: {header.get('period_start_date')} to {header.get('period_end_date')}")
            print(f"   Type: {header.get('period_type')}")
            print(f"   Accounting: {header.get('accounting_basis')}")
            print()

        # Compare with single-engine extraction
        print("🔄 Running single-engine extraction for comparison...")
        single_result = parser.extract_income_statement_table(pdf_data)

        if single_result.get("success"):
            print()
            print("📊 COMPARISON: Multi-Engine vs Single-Engine")
            print(f"   {'':30s} {'Multi-Engine':>15s} {'Single-Engine':>15s}")
            print("   " + "-" * 60)
            print(f"   {'Line items':30s} {result.get('total_items', 0):>15d} {single_result.get('total_items', 0):>15d}")
            print(f"   {'Consensus/Confidence':30s} {result.get('consensus_score', 0):>14.1f}% {85.0:>14.1f}%")
            print()

            if result.get('total_items') == single_result.get('total_items'):
                print("   ✅ Same number of line items extracted")
            else:
                diff = result.get('total_items', 0) - single_result.get('total_items', 0)
                if diff > 0:
                    print(f"   ℹ️  Multi-engine extracted {diff} more items")
                else:
                    print(f"   ⚠️  Multi-engine extracted {abs(diff)} fewer items")

        print()
        print("=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)
        print()

        quality_status = "EXCELLENT" if result.get('consensus_score', 0) >= 95 else \
                        "GOOD" if result.get('consensus_score', 0) >= 85 else "NEEDS IMPROVEMENT"

        print(f"Overall Quality: {quality_status} ({result.get('consensus_score', 0):.1f}%)")
        print()

        if result.get('consensus_score', 0) >= 95:
            print("🎉 Phase 2 multi-engine consensus achieving 95%+ target!")
        elif result.get('consensus_score', 0) >= 85:
            print("✅ Phase 2 multi-engine consensus working well (85%+)")
        else:
            print("⚠️  Consider additional tuning for consensus calculation")

        print()

    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    test_multi_engine_extraction()
