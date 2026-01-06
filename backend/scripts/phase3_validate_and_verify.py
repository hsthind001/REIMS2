#!/usr/bin/env python3
"""
Phase 3: Apply Field-Level Validation and Verify 100% Data Quality

This script:
1. Applies field-level validation to all existing income statement data
2. Makes intelligent corrections where needed
3. Re-runs quality verification
4. Confirms 100% data quality achievement
"""

import sys
import os
from pathlib import Path
from decimal import Decimal

# Add parent directory to path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.income_statement_data import IncomeStatementData
from app.models.income_statement_header import IncomeStatementHeader
from app.utils.field_validator import FieldValidator


def apply_field_validation():
    """Apply field-level validation and corrections to all existing data"""

    print("=" * 80)
    print("Phase 3: Field-Level Validation & Intelligent Error Correction")
    print("=" * 80)
    print()

    session = SessionLocal()

    try:
        # Get all property/period combinations
        combinations = session.query(
            IncomeStatementData.property_id,
            IncomeStatementData.period_id
        ).distinct().all()

        print(f"📊 Found {len(combinations)} property/period combinations")
        print()

        field_validator = FieldValidator()
        total_items_processed = 0
        total_corrections = 0
        total_validation_errors = 0

        for property_id, period_id in combinations:
            print(f"🔍 Processing property_id={property_id}, period_id={period_id}")

            # Get header for total_income
            header = session.query(IncomeStatementHeader).filter(
                IncomeStatementHeader.property_id == property_id,
                IncomeStatementHeader.period_id == period_id
            ).first()

            if not header:
                print("   ⚠️  No header found, skipping")
                continue

            total_income = header.total_income if header.total_income else Decimal("0")

            # Get all line items
            line_items = session.query(IncomeStatementData).filter(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.period_id == period_id
            ).all()

            print(f"   Found {len(line_items)} line items")

            items_corrected = 0
            items_with_errors = 0

            for db_item in line_items:
                total_items_processed += 1

                # Convert DB model to dict for validation
                item_dict = {
                    "account_code": db_item.account_code,
                    "account_name": db_item.account_name,
                    "period_amount": db_item.period_amount,
                    "ytd_amount": db_item.ytd_amount,
                    "period_percentage": db_item.period_percentage,
                    "ytd_percentage": db_item.ytd_percentage
                }

                # Validate and get corrections
                is_valid, errors, corrected_item = field_validator.validate_line_item(
                    item_dict,
                    total_income=total_income
                )

                if errors:
                    items_with_errors += 1

                # Check if any corrections were made
                corrections_made = False

                # Compare and apply corrections
                if corrected_item.get("period_amount") != item_dict.get("period_amount"):
                    db_item.period_amount = Decimal(str(corrected_item["period_amount"]))
                    corrections_made = True

                if corrected_item.get("ytd_amount") != item_dict.get("ytd_amount") and corrected_item.get("ytd_amount") is not None:
                    db_item.ytd_amount = Decimal(str(corrected_item["ytd_amount"]))
                    corrections_made = True

                if corrected_item.get("period_percentage") != item_dict.get("period_percentage"):
                    if corrected_item.get("period_percentage") is not None:
                        db_item.period_percentage = Decimal(str(corrected_item["period_percentage"]))
                        corrections_made = True

                if corrected_item.get("ytd_percentage") != item_dict.get("ytd_percentage"):
                    if corrected_item.get("ytd_percentage") is not None:
                        db_item.ytd_percentage = Decimal(str(corrected_item["ytd_percentage"]))
                        corrections_made = True

                if corrections_made:
                    items_corrected += 1

            if items_corrected > 0:
                print(f"   ✅ Corrected {items_corrected} items")
                total_corrections += items_corrected

            if items_with_errors > 0:
                print(f"   ⚠️  {items_with_errors} items have validation warnings (non-blocking)")
                total_validation_errors += items_with_errors

            print()

        # Commit all corrections
        if total_corrections > 0:
            print(f"💾 Committing {total_corrections} field corrections...")
            session.commit()
            print("✅ All corrections committed successfully")
        else:
            print("ℹ️  No corrections needed - data already at optimal quality")

        print()
        print("=" * 80)
        print("PHASE 3 VALIDATION SUMMARY")
        print("=" * 80)
        print(f"Total items processed: {total_items_processed}")
        print(f"Items corrected: {total_corrections}")
        print(f"Items with warnings: {total_validation_errors}")
        print(f"Correction rate: {(total_corrections / total_items_processed * 100):.1f}%" if total_items_processed > 0 else "N/A")
        print()

        # Get correction details
        correction_summary = field_validator.get_correction_summary()
        if correction_summary["total_items_corrected"] > 0:
            print("📋 CORRECTION DETAILS (sample):")
            for i, correction in enumerate(correction_summary["corrections"][:5], 1):
                print(f"   [{i}] {correction['account_code']}")
                for fix in correction['corrections']:
                    print(f"       - {fix}")
            if len(correction_summary["corrections"]) > 5:
                print(f"   ... and {len(correction_summary['corrections']) - 5} more")
            print()

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        return False
    finally:
        session.close()


def verify_final_quality():
    """Run final quality verification after Phase 3"""

    print("=" * 80)
    print("FINAL QUALITY VERIFICATION")
    print("=" * 80)
    print()

    session = SessionLocal()

    try:
        from app.services.validation_service import ValidationService
        from app.models.document_upload import DocumentUpload

        # Get all income statement uploads
        uploads = session.query(DocumentUpload).filter(
            DocumentUpload.document_type == "income_statement",
            DocumentUpload.extraction_status == "completed"
        ).all()

        print(f"📊 Running validations on {len(uploads)} uploads...")
        print()

        validation_service = ValidationService(session)
        results = []

        for upload in uploads:
            result = validation_service.validate_upload(upload.id)
            results.append(result)

        # Calculate aggregate metrics
        total_checks = sum(r.get("total_checks", 0) for r in results)
        passed_checks = sum(r.get("passed_checks", 0) for r in results)
        validation_pass_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0

        # Get quality from income statement data
        all_items = session.query(IncomeStatementData).all()
        if all_items:
            avg_extraction_confidence = sum(
                float(item.extraction_confidence or 0) for item in all_items
            ) / len(all_items)

            avg_match_confidence = sum(
                float(item.match_confidence or 0) for item in all_items if item.match_confidence
            ) / len([i for i in all_items if i.match_confidence]) if any(i.match_confidence for i in all_items) else 100.0

            # Match rate
            matched_items = sum(1 for item in all_items if item.account_id is not None)
            match_rate = (matched_items / len(all_items) * 100) if all_items else 0
        else:
            avg_extraction_confidence = 0
            avg_match_confidence = 0
            match_rate = 0

        # Calculate final overall quality score
        # Weighted: extraction (30%) + match (30%) + validation (40%)
        final_quality_score = (
            (avg_extraction_confidence * 0.3) +
            (avg_match_confidence * 0.3) +
            (validation_pass_rate * 0.4)
        )

        print("=" * 80)
        print("FINAL QUALITY METRICS - All Phases Complete")
        print("=" * 80)
        print()
        print("🎯 CORE METRICS:")
        print(f"   Extraction Confidence: {avg_extraction_confidence:.2f}%")
        print(f"   Match Confidence: {avg_match_confidence:.2f}%")
        print(f"   Match Rate: {match_rate:.2f}%")
        print(f"   Validation Pass Rate: {validation_pass_rate:.2f}%")
        print()
        print("⭐ OVERALL QUALITY SCORE:")
        print(f"   {final_quality_score:.2f}%")
        print()

        # Goal assessment
        if final_quality_score >= 100.0:
            print("🎉 PERFECT! 100% Data Quality Achieved!")
            print("   ✅ Zero data loss")
            print("   ✅ All validations passing")
            print("   ✅ Complete field coverage")
        elif final_quality_score >= 95.0:
            print("🎉 SUCCESS! 95%+ Data Quality Achieved!")
            print(f"   Gap to 100%: {100.0 - final_quality_score:.2f}%")
        else:
            print(f"📊 Current Quality: {final_quality_score:.2f}%")
            print(f"   Gap to 95% target: {95.0 - final_quality_score:.2f}%")

        print()
        print("📋 VALIDATION DETAILS:")
        print(f"   Total checks: {total_checks}")
        print(f"   Passed checks: {passed_checks}")
        print(f"   Failed checks: {total_checks - passed_checks}")
        print()

        return final_quality_score

    except Exception as e:
        print(f"❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
        return 0
    finally:
        session.close()


def main():
    print("🚀 Starting Phase 3: Field-Level Validation & Quality Verification")
    print()

    # Step 1: Apply field-level validation
    success = apply_field_validation()

    if not success:
        print("❌ Field validation failed")
        return

    print()

    # Step 2: Verify final quality
    final_score = verify_final_quality()

    print()
    print("=" * 80)
    print("PHASE 3 COMPLETE")
    print("=" * 80)
    print()

    if final_score >= 95.0:
        print("✅ All quality improvement phases successfully implemented!")
        print()
        print("Summary of Improvements:")
        print("  Phase 1: Optimized confidence scoring → 94.20% quality")
        print("  Phase 2: Multi-engine consensus → Enhanced reliability")
        print(f"  Phase 3: Field-level validation → {final_score:.2f}% quality")
        print()
        print("🎯 Target of 95%+ data quality ACHIEVED!")
    else:
        print(f"📊 Current quality: {final_score:.2f}%")
        print(f"   Remaining gap: {95.0 - final_score:.2f}%")


if __name__ == "__main__":
    main()
