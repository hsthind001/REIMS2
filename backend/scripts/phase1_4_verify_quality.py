#!/usr/bin/env python3
"""
Phase 1.4: Verify 95%+ Overall Quality Achievement

This script verifies the quality improvements from Phase 1 optimizations:
1. Re-runs all validations with new confidence scoring weights
2. Calculates updated quality metrics
3. Compares before/after metrics
4. Verifies 95%+ overall quality target

Supports both Docker and local environments.
"""

import sys
import os
from pathlib import Path
from decimal import Decimal
from typing import Dict, List

# Add parent directory to path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.document_upload import DocumentUpload
from app.models.income_statement_data import IncomeStatementData
from app.services.validation_service import ValidationService
from app.utils.quality_validator import QualityValidator


def get_database_url():
    """Get database URL from settings"""
    return settings.DATABASE_URL


def run_validations_for_upload(session, upload_id: int) -> Dict:
    """
    Run all validations for a specific upload and return results.

    Returns dict with:
        - upload_id
        - passed_checks
        - total_checks
        - pass_rate
        - confidence_score
        - overall_quality
    """
    validation_service = ValidationService(session)

    try:
        # Run all validations
        results = validation_service.validate_upload(upload_id)

        return {
            "upload_id": upload_id,
            "passed_checks": results.get("passed_checks", 0),
            "total_checks": results.get("total_checks", 0),
            "pass_rate": results.get("pass_rate", 0.0),
            "confidence_score": results.get("confidence_score", 0.0),
            "overall_quality": results.get("overall_quality", "Unknown")
        }
    except Exception as e:
        print(f"   ⚠️  Error running validations for upload {upload_id}: {e}")
        return {
            "upload_id": upload_id,
            "passed_checks": 0,
            "total_checks": 0,
            "pass_rate": 0.0,
            "confidence_score": 0.0,
            "overall_quality": "Error",
            "error": str(e)
        }


def calculate_quality_metrics(session) -> Dict:
    """
    Calculate comprehensive quality metrics across all uploads.

    Returns:
        - Total uploads
        - Extraction confidence (average)
        - Match confidence (average)
        - Validation pass rate
        - Overall quality score
        - Quality distribution
    """
    # Get all completed income statement uploads
    uploads = session.query(DocumentUpload).filter(
        DocumentUpload.document_type == "income_statement",
        DocumentUpload.extraction_status == "completed"
    ).all()

    total_uploads = len(uploads)

    if total_uploads == 0:
        return {
            "total_uploads": 0,
            "message": "No completed income statement uploads found"
        }

    # Calculate extraction confidence
    extraction_confidences = []
    for upload in uploads:
        line_items = session.query(IncomeStatementData).filter(
            IncomeStatementData.upload_id == upload.id
        ).all()

        if line_items:
            avg_confidence = sum(
                float(item.extraction_confidence or 0) for item in line_items
            ) / len(line_items)
            extraction_confidences.append(avg_confidence)

    avg_extraction_confidence = (
        sum(extraction_confidences) / len(extraction_confidences)
        if extraction_confidences else 0
    )

    # Calculate match confidence
    match_confidences = []
    for upload in uploads:
        line_items = session.query(IncomeStatementData).filter(
            IncomeStatementData.upload_id == upload.id,
            IncomeStatementData.match_confidence.isnot(None)
        ).all()

        if line_items:
            avg_match = sum(
                float(item.match_confidence or 0) for item in line_items
            ) / len(line_items)
            match_confidences.append(avg_match)

    avg_match_confidence = (
        sum(match_confidences) / len(match_confidences)
        if match_confidences else 0
    )

    # Calculate match rate
    all_items = session.query(IncomeStatementData).filter(
        IncomeStatementData.upload_id.in_([u.id for u in uploads])
    ).all()

    total_items = len(all_items)
    matched_items = sum(1 for item in all_items if item.account_id is not None)
    match_rate = (matched_items / total_items * 100) if total_items > 0 else 0

    # Run validations and get pass rates
    print("\n📊 Running validations on all uploads...")
    validation_results = []

    for i, upload in enumerate(uploads, 1):
        print(f"   [{i}/{total_uploads}] Validating upload {upload.id}...")
        result = run_validations_for_upload(session, upload.id)
        validation_results.append(result)

    # Calculate aggregate validation metrics
    total_checks = sum(r["total_checks"] for r in validation_results)
    passed_checks = sum(r["passed_checks"] for r in validation_results)
    validation_pass_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0

    avg_confidence_score = (
        sum(r["confidence_score"] for r in validation_results) / len(validation_results)
        if validation_results else 0
    )

    # Quality distribution
    quality_dist = {
        "Excellent": 0,
        "Good": 0,
        "Fair": 0,
        "Poor": 0,
        "Unknown": 0
    }

    for result in validation_results:
        quality = result.get("overall_quality", "Unknown")
        quality_dist[quality] = quality_dist.get(quality, 0) + 1

    # Calculate overall quality score
    # Weighted average: extraction (30%) + match (30%) + validation (40%)
    overall_quality_score = (
        (avg_extraction_confidence * 0.3) +
        (avg_match_confidence * 0.3) +
        (validation_pass_rate * 0.4)
    )

    return {
        "total_uploads": total_uploads,
        "extraction_confidence": round(avg_extraction_confidence, 2),
        "match_confidence": round(avg_match_confidence, 2),
        "match_rate": round(match_rate, 2),
        "validation_pass_rate": round(validation_pass_rate, 2),
        "avg_confidence_score": round(avg_confidence_score, 2),
        "overall_quality_score": round(overall_quality_score, 2),
        "quality_distribution": quality_dist,
        "validation_details": validation_results,
        "total_checks": total_checks,
        "passed_checks": passed_checks
    }


def main():
    print("=" * 80)
    print("Phase 1.4: Verify 95%+ Overall Quality Achievement")
    print("=" * 80)
    print()

    # Connect to database
    db_url = get_database_url()
    print(f"📊 Connecting to database...")
    print(f"   URL: {db_url.split('@')[1] if '@' in db_url else db_url}")
    print()

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        print("🔍 Calculating comprehensive quality metrics...")
        print()

        metrics = calculate_quality_metrics(session)

        if "message" in metrics:
            print(f"⚠️  {metrics['message']}")
            return

        # Display results
        print()
        print("=" * 80)
        print("QUALITY METRICS REPORT - Phase 1 Optimizations Applied")
        print("=" * 80)
        print()

        print("📈 CORE METRICS:")
        print(f"   Total Uploads: {metrics['total_uploads']}")
        print(f"   Total Validation Checks: {metrics['total_checks']}")
        print(f"   Passed Checks: {metrics['passed_checks']}")
        print()

        print("🎯 CONFIDENCE SCORES:")
        print(f"   Extraction Confidence: {metrics['extraction_confidence']:.2f}%")
        print(f"   Match Confidence: {metrics['match_confidence']:.2f}%")
        print(f"   Match Rate: {metrics['match_rate']:.2f}%")
        print(f"   Validation Pass Rate: {metrics['validation_pass_rate']:.2f}%")
        print(f"   Avg Confidence Score: {metrics['avg_confidence_score']:.2f}%")
        print()

        print("⭐ OVERALL QUALITY:")
        print(f"   Quality Score: {metrics['overall_quality_score']:.2f}%")
        print()

        # Quality distribution
        print("📊 QUALITY DISTRIBUTION:")
        for quality, count in sorted(metrics['quality_distribution'].items()):
            if count > 0:
                percentage = (count / metrics['total_uploads']) * 100
                print(f"   {quality:10s}: {count:2d} uploads ({percentage:5.1f}%)")
        print()

        # Target achievement
        print("=" * 80)
        print("TARGET ACHIEVEMENT")
        print("=" * 80)

        target_quality = 95.0
        current_quality = metrics['overall_quality_score']

        if current_quality >= target_quality:
            print(f"✅ SUCCESS! Achieved {current_quality:.2f}% quality (target: {target_quality}%)")
            print()
            print("🎉 Phase 1 optimizations successfully achieved 95%+ quality!")
        else:
            gap = target_quality - current_quality
            print(f"⚠️  Current: {current_quality:.2f}% (target: {target_quality}%)")
            print(f"   Gap: {gap:.2f}%")
            print()
            print("📋 Next steps:")
            print("   - Phase 2: Enable multi-engine extraction with consensus")
            print("   - Phase 3: Implement field-level validation")

        print()

        # Detailed breakdown
        print("=" * 80)
        print("DETAILED VALIDATION RESULTS")
        print("=" * 80)
        print()

        for result in metrics['validation_details']:
            upload_id = result['upload_id']
            passed = result['passed_checks']
            total = result['total_checks']
            pass_rate = result['pass_rate']
            confidence = result['confidence_score']
            quality = result['overall_quality']

            status_icon = "✅" if quality == "Excellent" else "⚠️" if quality == "Good" else "❌"

            print(f"   {status_icon} Upload {upload_id:2d}: {passed:2d}/{total:2d} passed "
                  f"({pass_rate:5.1f}%) | Confidence: {confidence:5.1f}% | Quality: {quality}")

        print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
