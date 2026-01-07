"""
Fix Period Type for All Years (2023, 2024, 2025)

This script fixes the period_type mislabeling for all years where
income statements are labeled as "Annual" but contain MONTHLY data.

Usage:
    docker compose exec -T -u root backend python /app/scripts/fix_all_years_period_type.py
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
from datetime import datetime


def detect_monthly_vs_annual(db, property_id: int, year: int):
    """
    Detect if income statements are actually monthly even though labeled as annual
    """
    query = db.query(
        IncomeStatementData.period_type,
        func.count(func.distinct(IncomeStatementData.period_id)).label('period_count')
    ).join(
        FinancialPeriod,
        IncomeStatementData.period_id == FinancialPeriod.id
    ).filter(
        IncomeStatementData.property_id == property_id,
        FinancialPeriod.period_year == year
    ).group_by(IncomeStatementData.period_type).first()

    if not query:
        return None

    period_type, period_count = query

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

    # Get all periods for this property/year
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
        print("  CRITICAL FIX: Period Type Mislabeling for All Years")
        print("="*100)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        property_id = 1  # ESP001
        years = [2023, 2024, 2025]

        total_fixed = 0

        # Fix period types for each year
        for year in years:
            fixed_count = fix_period_types(db, property_id, year)
            total_fixed += fixed_count

        if total_fixed == 0:
            print("\n✓ No fixes needed for any year")
            return

        # Recalculate metrics with correct period types for all years
        print(f"\n{'='*100}")
        print(f"Recalculating Financial Metrics with Corrected Period Types")
        print(f"{'='*100}\n")

        metrics_service = MetricsService(db)

        for year in years:
            print(f"\n--- Year {year} ---\n")

            periods = db.query(FinancialPeriod).filter(
                FinancialPeriod.property_id == property_id,
                FinancialPeriod.period_year == year
            ).order_by(FinancialPeriod.period_month.desc()).all()

            if not periods:
                print(f"No periods found for year {year}")
                continue

            print(f"{'Period':<10} {'DSCR (After)':<15} {'NOI (After)':<20} {'Status':<10}")
            print("-"*60)

            for period in periods:
                period_label = f"{period.period_year}-{period.period_month:02d}"

                try:
                    # Recalculate
                    new_metrics = metrics_service.calculate_all_metrics(property_id, period.id)

                    new_noi = new_metrics.net_operating_income if new_metrics.net_operating_income else 0
                    new_dscr = new_metrics.dscr if new_metrics.dscr else None

                    # Determine status
                    if new_dscr is None:
                        status = "⚠️  NULL"
                    elif new_dscr < 1.10:
                        status = "🔴 CRIT"
                    elif new_dscr < 1.25:
                        status = "🟡 WARN"
                    else:
                        status = "🟢 OK"

                    new_noi_str = f"${new_noi:,.0f}"
                    new_dscr_str = f"{new_dscr:.4f}" if new_dscr else "NULL"

                    print(f"{period_label:<10} {new_dscr_str:<15} {new_noi_str:<20} {status:<10}")
                except Exception as e:
                    print(f"{period_label:<10} ERROR: {str(e)}")

        print(f"\n{'='*100}")
        print("  FIX COMPLETE")
        print(f"{'='*100}")
        print(f"Fixed {total_fixed} income statement records across {len(years)} years")
        print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*100}\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()
