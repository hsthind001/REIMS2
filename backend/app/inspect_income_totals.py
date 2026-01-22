import sys
from sqlalchemy import select, text, func
from decimal import Decimal

# Add /app to path
sys.path.append('/app')

from app.db.database import SessionLocal
from app.models.income_statement_data import IncomeStatementData

def main():
    db = SessionLocal()
    try:
        property_id = 11
        period_id = 169
        
        print(f"Checking Income Statement data for Property {property_id}, Period {period_id}...")
        print("=" * 80)
        
        # Check for "Total" account codes
        total_codes = [
            ('4990-0000', 'Total Income'),
            ('5990-0000', 'Total Operating Expenses'),
            ('6990-0000', 'Total Additional Expenses'),
            ('7990-0000', 'Net Operating Income'),
            ('9990-0000', 'Net Income')
        ]
        
        print("\n1. CHECKING FOR TOTAL ROWS:")
        print("-" * 80)
        for code, name in total_codes:
            result = db.query(IncomeStatementData).filter(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.period_id == period_id,
                IncomeStatementData.account_code == code
            ).first()
            
            if result:
                print(f"✓ {code} ({name}): ${result.period_amount:,.2f}")
            else:
                print(f"✗ {code} ({name}): MISSING")
        
        # Check for rows marked as is_total or is_subtotal
        print("\n\n2. CHECKING FOR ROWS MARKED AS 'is_total' or 'is_subtotal':")
        print("-" * 80)
        
        total_rows = db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.is_total == True
        ).all()
        
        print(f"Found {len(total_rows)} rows with is_total=True:")
        for row in total_rows:
            print(f"  {row.account_code} - {row.account_name}: ${row.period_amount:,.2f}")
        
        subtotal_rows = db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.is_subtotal == True
        ).all()
        
        print(f"\nFound {len(subtotal_rows)} rows with is_subtotal=True:")
        for row in subtotal_rows:
            print(f"  {row.account_code} - {row.account_name}: ${row.period_amount:,.2f}")
        
        # Calculate sums manually
        print("\n\n3. CALCULATED SUMS (What validation expects):")
        print("-" * 80)
        
        # Income sum (4010-4091)
        income_sum = db.query(func.sum(IncomeStatementData.period_amount)).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code >= '4010-0000',
            IncomeStatementData.account_code < '4990-0000',
            IncomeStatementData.is_calculated == False
        ).scalar() or Decimal('0')
        print(f"Sum of Income Items (4010-4091): ${income_sum:,.2f}")
        
        # Operating expenses sum (5010-5989)
        opex_sum = db.query(func.sum(IncomeStatementData.period_amount)).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code >= '5010-0000',
            IncomeStatementData.account_code < '5990-0000',
            IncomeStatementData.is_calculated == False
        ).scalar() or Decimal('0')
        print(f"Sum of Operating Expenses (5010-5989): ${opex_sum:,.2f}")
        
        # Additional expenses sum (6010-6989)
        addl_sum = db.query(func.sum(IncomeStatementData.period_amount)).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code >= '6010-0000',
            IncomeStatementData.account_code < '6990-0000',
            IncomeStatementData.is_calculated == False
        ).scalar() or Decimal('0')
        print(f"Sum of Additional Expenses (6010-6989): ${addl_sum:,.2f}")
        
        print("\n\n4. SAMPLE DATA (First 10 income items):")
        print("-" * 80)
        sample = db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id
        ).order_by(IncomeStatementData.account_code).limit(10).all()
        
        for row in sample:
            print(f"{row.account_code} | {row.account_name[:40]:40} | ${row.period_amount:12,.2f} | Total:{row.is_total} | Calc:{row.is_calculated}")

    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
