"""
Verify Collections Quality Analysis Values

Checking if the values shown on the dashboard are correct for Property 11, Period 169.
"""
import sys
from decimal import Decimal
sys.path.append('/app')

from app.db.database import SessionLocal
from app.models.rent_roll_data import RentRollData
from app.models.income_statement_data import IncomeStatementData
from sqlalchemy import func

def main():
    db = SessionLocal()
    try:
        property_id = 11
        period_id = 169
        
        print("=" * 80)
        print("COLLECTIONS QUALITY ANALYSIS - DATA VERIFICATION")
        print("=" * 80)
        print(f"Property: {property_id}, Period: {period_id}\n")
        
        # 1. Check Total Rent from Rent Roll
        print("1. RENT ROLL DATA:")
        print("-" * 80)
        
        rent_roll_tenants = db.query(RentRollData).filter(
            RentRollData.property_id == property_id,
            RentRollData.period_id == period_id
        ).all()
        
        total_monthly_rent = sum((t.monthly_rent or Decimal('0')) for t in rent_roll_tenants)
        total_annual_rent = sum((t.annual_rent or Decimal('0')) for t in rent_roll_tenants)
        occupied_tenants = sum(1 for t in rent_roll_tenants if (t.occupancy_status or '').lower() in ['occupied', 'leased'])
        
        print(f"Total Tenants: {len(rent_roll_tenants)}")
        print(f"Occupied Tenants: {occupied_tenants}")
        print(f"Total Monthly Rent: ${total_monthly_rent:,.2f}")
        print(f"Total Annual Rent: ${total_annual_rent:,.2f}")
        
        # 2. Check Income Statement Revenue
        print("\n2. INCOME STATEMENT REVENUE:")
        print("-" * 80)
        
        # Base Rentals (4010-0000)
        base_rentals = db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code == '4010-0000'
        ).first()
        
        # Total Income (4990-0000)
        total_income = db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code == '4990-0000'
        ).first()
        
        print(f"Base Rentals (4010-0000): ${base_rentals.period_amount if base_rentals else 0:,.2f}")
        print(f"Total Income (4990-0000): ${total_income.period_amount if total_income else 0:,.2f}")
        
        # 3. Check for A/R accounts in Balance Sheet
        print("\n3. ACCOUNTS RECEIVABLE (Balance Sheet):")
        print("-" * 80)
        
        from app.models.balance_sheet_data import BalanceSheetData
        
        # A/R Tenants account (typically 1200-0000 range)
        ar_accounts = db.query(BalanceSheetData).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.period_id == period_id,
            BalanceSheetData.account_code.like('12%')
        ).all()
        
        if ar_accounts:
            for ar in ar_accounts:
                print(f"{ar.account_code} - {ar.account_name}: ${ar.amount:,.2f}")
        else:
            print("No A/R accounts found in Balance Sheet")
        
        # 4. Calculate expected values
        print("\n4. EXPECTED COLLECTIONS METRICS:")
        print("-" * 80)
        
        if base_rentals and total_monthly_rent > 0:
            # Collections Rate = Cash Collected / Rent Billed
            # Assuming cash collected = base rentals from IS
            collections_rate = (base_rentals.period_amount / total_monthly_rent) * 100
            print(f"Collections Rate: {collections_rate:.2f}%")
            print(f"  Formula: (Base Rentals ${base_rentals.period_amount:,.2f} / Monthly Rent ${total_monthly_rent:,.2f}) * 100")
        
        # The $744,533 shown might be Cash Collected
        cash_collected = Decimal('744533')
        if total_monthly_rent > 0:
            rate_from_744k = (cash_collected / total_monthly_rent) * 100
            print(f"\nIf Cash Collected = $744,533:")
            print(f"  Collections Rate would be: {rate_from_744k:.2f}%")
        
        print("\n5. DASHBOARD VALUES TO CHECK:")
        print("-" * 80)
        print("Dashboard shows:")
        print("  - Cash Collected: $744,533")
        print("  - Income Received: $0")
        print("  - Overall Collections Rate: 0.0%")
        print("  - Total A/R: $0")
        print("  - All aging buckets: $0")
        
        print("\nPOTENTIAL ISSUES:")
        print("  ❌ Income Received showing $0 (should be Monthly Rent)")
        print("  ❌ Collections Rate showing 0.0% (calculation error)")
        print("  ❌ A/R accounts showing $0 (may not exist in Balance Sheet)")

    except Exception as e:
        import traceback
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
