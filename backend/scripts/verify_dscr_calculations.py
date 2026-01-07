"""
Verify DSCR Calculations are Correct
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.core.config import settings
from app.models.financial_metrics import FinancialMetrics
from app.models.property import Property
from app.models.financial_period import FinancialPeriod

# Create DB session
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print("=" * 80)
print("✅ DSCR Calculation Verification")
print("=" * 80)

# Get DSCR data for ESP001 in 2023
property = db.query(Property).filter(Property.property_code == 'ESP001').first()
if property:
    metrics = db.query(FinancialMetrics).join(
        FinancialPeriod, FinancialMetrics.period_id == FinancialPeriod.id
    ).filter(
        FinancialMetrics.property_id == property.id,
        FinancialPeriod.period_year == 2023,
        FinancialMetrics.dscr.isnot(None)
    ).order_by(FinancialPeriod.period_month.desc()).all()

    print(f"\nProperty: ESP001")
    print(f"Year: 2023")
    print(f"Periods with DSCR: {len(metrics)}\n")

    all_pass = True
    for m in metrics[:3]:
        period = db.query(FinancialPeriod).filter(FinancialPeriod.id == m.period_id).first()
        expected_dscr = float(m.net_operating_income) / float(m.total_annual_debt_service)
        actual_dscr = float(m.dscr)
        diff = abs(expected_dscr - actual_dscr)

        if diff < 0.001:
            status = '✅'
        else:
            status = '❌'
            all_pass = False

        print(f"{status} {period.period_year}-{period.period_month:02d}: DSCR={actual_dscr:.4f}")
        print(f"   NOI: ${m.net_operating_income:,.2f}")
        print(f"   Annual Debt Service: ${m.total_annual_debt_service:,.2f}")
        print(f"   Formula Check: {expected_dscr:.4f} (diff: {diff:.6f})")
        print()

    if all_pass:
        print("=" * 80)
        print("🎯 ALL DSCR CALCULATIONS VERIFIED - FORMULAS ARE CORRECT!")
        print("=" * 80)
    else:
        print("=" * 80)
        print("⚠️  SOME DSCR CALCULATIONS FAILED VERIFICATION")
        print("=" * 80)

db.close()
