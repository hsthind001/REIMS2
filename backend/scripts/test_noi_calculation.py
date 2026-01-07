"""
Test NOI Calculation - Debug Script

This script tests NOI calculation for a specific property/period to understand
why NOI is being stored as $0.00.
"""
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.database import SessionLocal
from app.services.metrics_service import MetricsService
from decimal import Decimal

def test_noi_calculation():
    """Test NOI calculation for ESP001, period 98 (2025-11)"""
    db = SessionLocal()

    try:
        property_id = 1  # ESP001
        period_id = 98    # 2025-11

        print("="*80)
        print("Testing NOI Calculation")
        print("="*80)
        print(f"Property ID: {property_id}")
        print(f"Period ID: {period_id}")
        print()

        # Create MetricsService
        metrics_service = MetricsService(db)

        # Test calculate_income_statement_metrics directly
        print("--- Calling calculate_income_statement_metrics ---")
        metrics_data = metrics_service.calculate_income_statement_metrics(property_id, period_id)

        print("\nReturned metrics_data:")
        for key, value in metrics_data.items():
            if isinstance(value, Decimal):
                print(f"  {key}: ${value:,.2f}")
            else:
                print(f"  {key}: {value}")

        # Now test calculate_all_metrics
        print("\n" + "="*80)
        print("--- Calling calculate_all_metrics ---")
        metrics = metrics_service.calculate_all_metrics(property_id, period_id)

        print(f"\nStored in database:")
        print(f"  ID: {metrics.id}")
        print(f"  Property ID: {metrics.property_id}")
        print(f"  Period ID: {metrics.period_id}")
        print(f"  Total Revenue: ${metrics.total_revenue:,.2f}" if metrics.total_revenue else "  Total Revenue: NULL")
        print(f"  Net Operating Income: ${metrics.net_operating_income:,.2f}" if metrics.net_operating_income else "  Net Operating Income: NULL")
        print(f"  Total Annual Debt Service: ${metrics.total_annual_debt_service:,.2f}" if metrics.total_annual_debt_service else "  Total Annual Debt Service: NULL")
        print(f"  DSCR: {metrics.dscr}" if metrics.dscr else "  DSCR: NULL")

        # Calculate expected DSCR
        if metrics.net_operating_income and metrics.total_annual_debt_service:
            expected_dscr = metrics.net_operating_income / metrics.total_annual_debt_service
            print(f"\n  Expected DSCR: {expected_dscr:.4f}")

    finally:
        db.close()

if __name__ == "__main__":
    test_noi_calculation()
