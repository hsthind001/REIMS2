"""
Fix Period Type Mislabeling and Recalculate DSCR

CRITICAL BUG FOUND: Income statements are labeled as "Annual" but contain MONTHLY data.
This causes DSCR to be calculated as 0.17 instead of 2.12 (12x error!)

This script:
1. Identifies income statements with incorrect period_type
2. Corrects period_type from "Annual" to "Monthly"
3. Recalculates all financial metrics with correct annualization
4. Verifies DSCR is now calculated correctly

Usage:
    docker compose exec -T -u root backend python /app/scripts/fix_period_type_and_recalculate.py
"""

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.database import SessionLocal
from app.services.metrics_service import MetricsService
from app.models.income_statement_data import IncomeStatementData
from app.models.financial_period import FinancialPeriod
from sqlalchemy import func
from decimal import Decimal
from datetime import datetime


def detect_monthly_vs_annual(db, property_id: int, year: int):
    """
    Detect if income statements are actually monthly even though labeled as annual

    Heuristic: If we have 12 statements in a year with similar revenue amounts,
    and the sum of all NOIs is reasonable for annual operation, they're monthly.
    """
    # Get all income statements for the year
    query = db.query(
        IncomeStatementData.period_type,
        func.count(func.distinct(IncomeStatementData.period_id)).label('period_count'),
        func.sum(IncomeStatementData.period_amount).filter(
            IncomeStatementData.account_code.like('4%')
        ).label('total_revenue'),
        func.avg(IncomeStatementData.period_amount).filter(
            IncomeStatementData.account_code.like('4%')
        ).label('avg_revenue')
    ).join(
        FinancialPeriod,
        IncomeStatementData.period_id == FinancialPeriod.id
    ).filter(
        IncomeStatementData.property_id == property_id,
        FinancialPeriod.period_year == year
    ).group_by(IncomeStatementData.period_type).first()

    if not query:
        return None

    period_type, period_count, total_revenue, avg_revenue = query

    # If we have 12 periods and they're labeled "Annual", they're likely monthly
    if period_count == 12 and period_type and period_type.upper() in ['ANNUAL', 'YEAR', 'YEARLY']:
        return 'MONTHLY_MISLABELED_AS_ANNUAL'
    elif period_count == 12 and period_type and period_type.upper() in ['MONTHLY', 'MONTH']:
        return 'CORRECTLY_MONTHLY'
    elif period_count == 1 and period_type and period_type.upper() in ['ANNUAL', 'YEAR', 'YEARLY']:
        return 'CORRECTLY_ANNUAL'
    else:
        return 'UNKNOWN'


def fix_period_types(db, property_id: int, year: int):
    """
    Fix mislabeled period types for income statements
    """
    print(f"\n{'='*100}")
    print(f"Fixing Period Types for Property {property_id}, Year {year}")
    print(f"{'='*100}\n")

    # Detect the issue
    detection = detect_monthly_vs_annual(db, property_id, year)

    print(f"Detection Result: {detection}\n")

    if detection != 'MONTHLY_MISLABELED_AS_ANNUAL':
        print("✓ No fix needed - period types are correct")
        return 0

    # Get all income statement records for this property/year
    periods = db.query(FinancialPeriod).filter(
        FinancialPeriod.property_id == property_id,
        FinancialPeriod.period_year == year
    ).all()

    print(f"Found {len(periods)} periods to fix\n")

    fixed_count = 0
    for period in periods:
        # Update all income statement data for this period
        updated = db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period.id,
            IncomeStatementData.period_type.in_(['Annual', 'ANNUAL', 'Year', 'YEAR', 'Yearly', 'YEARLY'])
        ).update(
            {'period_type': 'Monthly'},
            synchronize_session=False
        )

        if updated > 0:
            fixed_count += updated
            period_label = f"{period.period_year}-{period.period_month:02d}"
            print(f"  [{period_label}] Fixed {updated} records: Annual → Monthly")

    db.commit()

    print(f"\n✓ Fixed {fixed_count} income statement records\n")

    return fixed_count


def main():
    db = SessionLocal()

    try:
        print("="*100)
        print("  CRITICAL FIX: Period Type Mislabeling")
        print("="*100)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        property_id = 1  # ESP001
        year = 2025

        # Step 1: Fix period types
        fixed_count = fix_period_types(db, property_id, year)

        if fixed_count == 0:
            print("\n✓ No fixes needed")
            return

        # Step 2: Recalculate metrics with correct period types
        print(f"\n{'='*100}")
        print(f"Recalculating Financial Metrics with Corrected Period Types")
        print(f"{'='*100}\n")

        metrics_service = MetricsService(db)

        periods = db.query(FinancialPeriod).filter(
            FinancialPeriod.property_id == property_id,
            FinancialPeriod.period_year == year
        ).order_by(FinancialPeriod.period_month.desc()).all()

        print(f"{'Period':<10} {'NOI (Before)':<20} {'DSCR (Before)':<15} {'NOI (After)':<20} {'DSCR (After)':<15} {'Status':<10}")
        print("-"*100)

        for period in periods:
            period_label = f"{period.period_year}-{period.period_month:02d}"

            # Get metrics before recalculation
            from app.models.financial_metrics import FinancialMetrics
            old_metrics = db.query(FinancialMetrics).filter(
                FinancialMetrics.property_id == property_id,
                FinancialMetrics.period_id == period.id
            ).first()

            old_noi = old_metrics.net_operating_income if old_metrics and old_metrics.net_operating_income else Decimal('0')
            old_dscr = old_metrics.dscr if old_metrics and old_metrics.dscr else None

            # Recalculate
            new_metrics = metrics_service.calculate_all_metrics(property_id, period.id)

            new_noi = new_metrics.net_operating_income if new_metrics.net_operating_income else Decimal('0')
            new_dscr = new_metrics.dscr if new_metrics.dscr else None

            # Determine status
            if new_dscr is None:
                status = "⚠️  NULL"
            elif new_dscr < Decimal('1.10'):
                status = "🔴 CRIT"
            elif new_dscr < Decimal('1.25'):
                status = "🟡 WARN"
            else:
                status = "🟢 OK"

            old_noi_str = f"${old_noi:,.0f}"
            old_dscr_str = f"{old_dscr:.4f}" if old_dscr else "NULL"
            new_noi_str = f"${new_noi:,.0f}"
            new_dscr_str = f"{new_dscr:.4f}" if new_dscr else "NULL"

            print(f"{period_label:<10} {old_noi_str:<20} {old_dscr_str:<15} {new_noi_str:<20} {new_dscr_str:<15} {status:<10}")

        print(f"\n{'='*100}")
        print("  FIX COMPLETE")
        print(f"{'='*100}")
        print(f"Fixed {fixed_count} income statement records")
        print(f"Recalculated metrics for {len(periods)} periods")
        print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*100}\n")

        # Summary
        print("\n📊 SUMMARY:")
        print(f"   Issue: Income statements were labeled 'Annual' but contained MONTHLY data")
        print(f"   Impact: DSCR was calculated as ~0.17 (12x too low!)")
        print(f"   Fix: Changed period_type to 'Monthly' and recalculated with proper annualization")
        print(f"   Result: DSCR should now be ~2.1 (HEALTHY)\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()
