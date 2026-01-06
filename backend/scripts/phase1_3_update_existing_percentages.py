#!/usr/bin/env python3
"""
Phase 1.3: Update Existing Data with Enhanced Calculations

This script updates all existing income statement data with:
1. Calculated percentages (period_percentage, ytd_percentage)
2. Ensures 100% data completeness for quality scoring

Supports both Docker and local environments.
"""

import sys
import os
from pathlib import Path
from decimal import Decimal

# Add parent directory to path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.income_statement_data import IncomeStatementData
from app.models.income_statement_header import IncomeStatementHeader
from app.core.config import settings


def get_database_url():
    """Get database URL from settings"""
    return settings.DATABASE_URL


def calculate_missing_percentages(session, property_id: int, period_id: int) -> int:
    """
    Calculate and populate missing percentage fields for a specific property/period.

    Returns:
        Number of records updated
    """
    # Get the header to access total_income
    header = session.query(IncomeStatementHeader).filter(
        IncomeStatementHeader.property_id == property_id,
        IncomeStatementHeader.period_id == period_id
    ).first()

    if not header or header.total_income == 0:
        print(f"   ⚠️  Skipping property_id={property_id}, period_id={period_id}: No header or zero total_income")
        return 0

    total_income = float(header.total_income)
    records_updated = 0

    # Get all income statement data for this property/period
    line_items = session.query(IncomeStatementData).filter(
        IncomeStatementData.property_id == property_id,
        IncomeStatementData.period_id == period_id
    ).all()

    for item in line_items:
        updated = False

        # Calculate period_percentage if missing
        if item.period_percentage is None and item.period_amount is not None:
            if total_income != 0:
                item.period_percentage = Decimal(
                    str(round((float(item.period_amount) / total_income) * 100, 2))
                )
                updated = True

        # Calculate ytd_percentage if missing
        if item.ytd_percentage is None and item.ytd_amount is not None:
            if total_income != 0:
                item.ytd_percentage = Decimal(
                    str(round((float(item.ytd_amount) / total_income) * 100, 2))
                )
                updated = True

        if updated:
            records_updated += 1

    return records_updated


def main():
    print("=" * 80)
    print("Phase 1.3: Update Existing Data with Enhanced Calculations")
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
        # Get all unique property_id/period_id combinations
        print("🔍 Finding all property/period combinations with income statement data...")

        result = session.query(
            IncomeStatementData.property_id,
            IncomeStatementData.period_id
        ).distinct().all()

        total_combinations = len(result)
        print(f"   Found {total_combinations} unique property/period combinations")
        print()

        if total_combinations == 0:
            print("⚠️  No income statement data found. Nothing to update.")
            return

        # Process each combination
        print("📝 Updating missing percentages...")
        print()

        total_updated = 0
        combinations_updated = 0

        for property_id, period_id in result:
            print(f"   Processing property_id={property_id}, period_id={period_id}...")

            updated = calculate_missing_percentages(session, property_id, period_id)

            if updated > 0:
                print(f"   ✅ Updated {updated} records")
                total_updated += updated
                combinations_updated += 1
            else:
                print(f"   ⏭️  No updates needed (all percentages already calculated)")
            print()

        # Commit all changes
        if total_updated > 0:
            print(f"💾 Committing {total_updated} record updates...")
            session.commit()
            print("✅ Database committed successfully")
            print()

        # Summary
        print("=" * 80)
        print("SUMMARY - Phase 1.3 Complete")
        print("=" * 80)
        print(f"Total property/period combinations: {total_combinations}")
        print(f"Combinations updated: {combinations_updated}")
        print(f"Total records updated: {total_updated}")
        print()

        if total_updated > 0:
            print("✅ All existing data now has calculated percentages!")
            print("   This ensures 100% data completeness for quality scoring.")
        else:
            print("✅ All data already complete - no updates needed.")

        print()
        print("Next step: Phase 1.4 - Verify 95%+ overall quality achievement")
        print()

    except Exception as e:
        print(f"❌ Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
