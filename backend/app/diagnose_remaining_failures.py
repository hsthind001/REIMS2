"""
Diagnose Remaining Validation Failures

After repair, we still have 4 failures. Let's diagnose them:
1. Total Additional Expenses mismatch
2. Net Income mismatch
3. Zero percentages
4. Period > YTD warning
"""
import sys
from decimal import Decimal
sys.path.append('/app')

from app.db.database import SessionLocal
from app.models.income_statement_data import IncomeStatementData
from app.models.income_statement_header import IncomeStatementHeader

def main():
    db = SessionLocal()
    try:
        property_id = 11
        period_id = 169
        
        print("DIAGNOSING REMAINING VALIDATION FAILURES")
        print("=" * 80)
        
        # Issue 1: Total Additional Expenses mismatch
        print("\n1. TOTAL ADDITIONAL EXPENSES MISMATCH")
        print("-" * 80)
        
        # Sum of detail items (6010-6189)
        addl_detail_sum = db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code >= '6010-0000',
            IncomeStatementData.account_code < '6190-0000',
            IncomeStatementData.is_calculated == False
        ).all()
        
        detail_sum = sum(item.period_amount for item in addl_detail_sum)
        print(f"Sum of detail items (6010-6189): ${detail_sum:,.2f}")
        print(f"Detail items count: {len(addl_detail_sum)}")
        
        # The total row (6190-0000)
        total_row = db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code == '6190-0000'
        ).first()
        
        if total_row:
            print(f"Total row (6190-0000): ${total_row.period_amount:,.2f}")
            print(f"Difference: ${abs(detail_sum - total_row.period_amount):,.2f}")
        
        # Check if there are items in the 6190-6199 range
        between_items = db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code >= '6190-0000',
            IncomeStatementData.account_code < '6200-0000'
        ).all()
        
        print(f"\nItems in 6190-6199 range:")
        for item in between_items:
            print(f"  {item.account_code} - {item.account_name}: ${item.period_amount:,.2f} [is_calc={item.is_calculated}]")
        
        # Issue 2: Net Income calculation
        print("\n\n2. NET INCOME CALCULATION")
        print("-" * 80)
        
        header = db.query(IncomeStatementHeader).filter(
            IncomeStatementHeader.property_id == property_id,
            IncomeStatementHeader.period_id == period_id
        ).first()
        
        print(f"NOI (Header): ${header.net_operating_income:,.2f}")
        print(f"Mortgage Interest (Header): ${header.mortgage_interest:,.2f}")
        print(f"Depreciation (Header): ${header.depreciation:,.2f}")
        print(f"Amortization (Header): ${header.amortization:,.2f}")
        
        other_total = header.mortgage_interest + header.depreciation + header.amortization
        print(f"Total 'Other' Expenses: ${other_total:,.2f}")
        
        calculated_net_income = header.net_operating_income - other_total
        print(f"NOI - Other = ${calculated_net_income:,.2f}")
        print(f"Net Income (Header): ${header.net_income:,.2f}")
        print(f"Difference: ${abs(calculated_net_income - header.net_income):,.2f}")
        
        # Issue 3: Zero percentages
        print("\n\n3. ZERO PERCENTAGES")
        print("-" * 80)
        
        items_with_zero_pct = db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.period_percentage == None
        ).count()
        
        print(f"Items with NULL period_percentage: {items_with_zero_pct}")
        
        # Check if any have percentages
        items_with_pct = db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.period_percentage != None
        ).all()
        
        print(f"Items WITH percentages: {len(items_with_pct)}")
        if items_with_pct:
            for item in items_with_pct[:5]:
                print(f"  {item.account_code}: {item.period_percentage}%")

    except Exception as e:
        import traceback
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
