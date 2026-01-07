"""
Recalculate All Financial Metrics and DSCR

This script recalculates all financial metrics for all properties and periods.
This ensures that DSCR values are up-to-date and accurate.

Usage:
    docker compose exec -T -u root backend python /app/scripts/recalculate_all_dscr.py

Or with specific year:
    docker compose exec -T -u root backend python /app/scripts/recalculate_all_dscr.py --year 2025
"""

import sys
import argparse
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.database import SessionLocal
from app.services.metrics_service import MetricsService
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from decimal import Decimal
from datetime import datetime


def recalculate_all(year: int = None):
    """
    Recalculate all financial metrics for all properties

    Args:
        year: Optional year filter (e.g., 2025). If None, recalculates all years.
    """
    db = SessionLocal()

    try:
        metrics_service = MetricsService(db)

        print("="*100)
        print("  DSCR RECALCULATION - Financial Metrics Update")
        print("="*100)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if year:
            print(f"Year Filter: {year}")
        print()

        # Get all properties
        properties = db.query(Property).order_by(Property.property_code).all()

        print(f"Found {len(properties)} properties\n")

        total_periods = 0
        successful = 0
        failed = 0
        skipped = 0

        for prop in properties:
            print("="*100)
            print(f"Property: {prop.property_code} - {prop.property_name}")
            print("="*100)

            # Get periods for this property
            query = db.query(FinancialPeriod).filter(
                FinancialPeriod.property_id == prop.id
            )

            if year:
                query = query.filter(FinancialPeriod.period_year == year)

            periods = query.order_by(
                FinancialPeriod.period_year.desc(),
                FinancialPeriod.period_month.desc()
            ).all()

            if not periods:
                print(f"  No periods found" + (f" for year {year}" if year else ""))
                print()
                continue

            print(f"Found {len(periods)} period(s)")
            print()

            for period in periods:
                total_periods += 1
                period_label = f"{period.period_year}-{period.period_month:02d}"

                try:
                    print(f"  [{period_label}] Recalculating metrics...")

                    # Recalculate all metrics
                    metrics = metrics_service.calculate_all_metrics(prop.id, period.id)

                    # Get calculated values
                    noi = metrics.net_operating_income if metrics.net_operating_income else Decimal('0')
                    debt_service = metrics.total_annual_debt_service if metrics.total_annual_debt_service else Decimal('0')
                    dscr = metrics.dscr if metrics.dscr else None

                    # Determine status
                    if dscr is None:
                        status = "⚠️  NULL"
                        reason = ""
                        if noi == 0:
                            reason = "(NOI = $0)"
                        elif debt_service == 0:
                            reason = "(Debt Service = $0)"
                        else:
                            reason = "(Missing data)"
                        status_detail = f"{status} {reason}"
                    elif dscr < Decimal('1.10'):
                        status_detail = "🔴 CRITICAL"
                    elif dscr < Decimal('1.25'):
                        status_detail = "🟡 WARNING"
                    else:
                        status_detail = "🟢 HEALTHY"

                    print(f"      NOI: ${noi:>15,.2f}")
                    print(f"      Debt Service: ${debt_service:>15,.2f}")
                    if dscr:
                        print(f"      DSCR: {dscr:>15.4f} {status_detail}")
                    else:
                        print(f"      DSCR: {' '*15}NULL {status_detail}")

                    successful += 1

                except Exception as e:
                    print(f"      ❌ ERROR: {str(e)}")
                    failed += 1

                print()

        # Summary
        print("="*100)
        print("  RECALCULATION SUMMARY")
        print("="*100)
        print(f"Total Periods Processed: {total_periods}")
        print(f"Successful: {successful} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Skipped: {skipped} ⏭️")
        print()
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*100)

        return successful, failed

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='Recalculate financial metrics and DSCR for all properties')
    parser.add_argument('--year', type=int, help='Only recalculate for specific year (e.g., 2025)')

    args = parser.parse_args()

    successful, failed = recalculate_all(year=args.year)

    # Exit with error code if any failures
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
