import sys
import os
from decimal import Decimal
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.db.database import Base, SessionLocal
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.forensic_reconciliation_session import ForensicReconciliationSession
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.forensic_discrepancy import ForensicDiscrepancy
from app.services.forensic_reconciliation_service import ForensicReconciliationService
from app.db.database import SessionLocal  # Import configured session

def verify_rule_failures():
    db = SessionLocal()
    try:
        print("Setting up test data...")
        # 1. Get or Create Property
        prop = db.query(Property).filter(Property.property_code == 'TEST_RULES').first()
        if not prop:
            prop = Property(
                property_code='TEST_RULES',
                property_name='Test Rules Property',
                property_type='Multifamily'
            )
            db.add(prop)
            db.commit()
            print(f"Created Property: {prop.id}")
        
        # 2. Get or Create Period
        period = db.query(FinancialPeriod).filter(
            FinancialPeriod.property_id == prop.id,
            FinancialPeriod.period_year == 2023, 
            FinancialPeriod.period_month == 10
        ).first()
        if not period:
            period = FinancialPeriod(
                property_id=prop.id,
                period_year=2023,
                period_month=10,
                period_start_date=date(2023, 10, 1),
                period_end_date=date(2023, 10, 31),
                is_closed=False
            )
            db.add(period)
            db.commit()
            print(f"Created Period: {period.id}")
            
        # 3. Create Session
        session = ForensicReconciliationSession(
            property_id=prop.id,
            period_id=period.id,
            session_type='full_reconciliation',
            status='in_progress'
        )
        db.add(session)
        db.commit()
        print(f"Created Session: {session.id}")
        
        # 4. Insert Data that VIOLATES rules
        # Rule BS_SPECIFIC_002_CASH_OP: BS.0122-0000 = 3375.45
        # We will insert 4000.00
        
        # Clear existing data for this period
        db.query(BalanceSheetData).filter(BalanceSheetData.period_id == period.id).delete()
        
        bs_data = BalanceSheetData(
            property_id=prop.id,
            period_id=period.id,
            account_code='0122-0000',
            account_name='Cash - Operating',
            amount=Decimal('4000.00'), # Violation! Expected 3375.45
            is_total=False,
            extraction_confidence=0.95,
            page_number=1,
            extraction_x0=100, extraction_y0=100, extraction_x1=200, extraction_y1=120
        )
        db.add(bs_data)
        
        # Rule IS_SPECIFIC_016_RM_LIGHTING: IS.5356-0000 = 4758.00
        # We will insert 5000.00
        is_data = IncomeStatementData(
            property_id=prop.id,
            period_id=period.id,
            account_code='5356-0000',
            account_name='R&M Lighting',
            period_amount=Decimal('5000.00'), # Violation! Expected 4758.00
            is_total=False,
            extraction_confidence=0.95,
            page_number=1
        )
        db.add(is_data)
        
        # Add required document uploads to satisfy service checks efficiently?
        # The service checks documents existence before creating session, but we created session manually.
        # validation logic might rely on them? No, calculated engine queries Data tables directly.
        
        db.commit()
        
        # 5. Run Validate Matches (this triggers rule evaluation)
        service = ForensicReconciliationService(db)
        print("Running validation...")
        result = service.validate_matches(session.id)
        
        print(f"Validation Result: Health Score {result['health_score']}")
        
        # 6. Verify Discrepancies
        discrepancies = db.query(ForensicDiscrepancy).filter(
            ForensicDiscrepancy.session_id == session.id,
            ForensicDiscrepancy.discrepancy_type == 'rule_failure'
        ).all()
        
        print(f"Found {len(discrepancies)} rule failures.")
        
        bs_failure = next((d for d in discrepancies if "BS_SPECIFIC_002_CASH_OP" in (d.description or "") or "Cash - Operating" in (d.description or "")), None)
        if bs_failure:
            print("✓ SUCCESS: Found BS_SPECIFIC_002_CASH_OP failure")
            print(f"  Expected: {bs_failure.expected_value}")
            print(f"  Actual: {bs_failure.actual_value}")
            print(f"  Diff: {bs_failure.difference}")
        else:
            print("✗ FAILURE: Did not find BS_SPECIFIC_002_CASH_OP failure")
            for d in discrepancies:
                print(f"  - {d.description}")

        is_failure = next((d for d in discrepancies if "IS_SPECIFIC_016_RM_LIGHTING" in (d.description or "") or "R&M Lighting" in (d.description or "")), None)
        if is_failure:
             print("✓ SUCCESS: Found IS_SPECIFIC_016_RM_LIGHTING failure")
        else:
             print("✗ FAILURE: Did not find IS_SPECIFIC_016_RM_LIGHTING failure")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_rule_failures()
