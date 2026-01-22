"""
Debug why Income Statement Total Revenue query returns $0
"""
import sys
from decimal import Decimal
sys.path.append('/app')

from app.db.database import SessionLocal
from app.models.income_statement_data import IncomeStatementData

def main():
    db = SessionLocal()
    try:
        property_id = 11
        period_id = 169
        
        print("=" * 80)
        print("DEBUGGING TOTAL REVENUE QUERY")
        print("=" * 80)
        
        # Test Query 1: Total with is_total=true
        print("\n1. Looking for is_total=True with line_category='INCOME':")
        print("-" * 80)
        
        total_rows = db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.line_category == 'INCOME',
            IncomeStatementData.is_total == True
        ).all()
        
        print(f"Found {len(total_rows)} rows")
        for row in total_rows:
            print(f"  {row.account_code} - {row.account_name}: ${row.period_amount:,.2f} [line_category={row.line_category}]")
        
        # Test Query 2: Sum of INCOME detail items  
        print("\n2. Sum of INCOME detail items (is_total=False, is_subtotal=False):")
        print("-" * 80)
        
        detail_sum = db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.line_category == 'INCOME',
            IncomeStatementData.is_total != True,
            IncomeStatementData.is_subtotal != True
        ).all()
        
        total = sum(row.period_amount for row in detail_sum)
        print(f"Sum of {len(detail_sum)} detail rows: ${total:,.2f}")
        
        # Test Query 3: Check how line_category is set
        print("\n3. Checking line_category values for all income items:")
        print("-" * 80)
        
        all_income = db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code.like('4%')
        ).all()
        
        print(f"Found {len(all_income)} income rows (account 4xxx)")
        categories = {}
        for row in all_income:
            cat = row.line_category or 'NULL'
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(f"{row.account_code}: ${row.period_amount:,.2f}")
        
        for cat, items in categories.items():
            print(f"\nline_category='{cat}': {len(items)} items")
            for item in items[:5]:  # Show first 5
                print(f"  {item}")
            if len(items) > 5:
                print(f"  ... and {len(items - 5)} more")
        
        # Test Query 4: Just get the total income row directly
        print("\n4. Direct query for Total Income (4990-0000):")
        print("-" * 80)
        
        total_income = db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code == '4990-0000'
        ).first()
        
        if total_income:
            print(f"Found: ${total_income.period_amount:,.2f}")
            print(f"  line_category: {total_income.line_category}")
            print(f"  is_total: {total_income.is_total}")
            print(f"  is_calculated: {total_income.is_calculated}")
        else:
            print("NOT FOUND!")

    except Exception as e:
        import traceback
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
