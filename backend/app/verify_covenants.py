"""
Verify Covenant Compliance Values

Check if the displayed covenant metrics are calculated correctly.
"""
import sys
sys.path.append('/app')

from app.db.database import SessionLocal
from app.models.balance_sheet_data import BalanceSheetData
from app.models.mortgage_statement_data import MortgageStatementData
from app.models.income_statement_header import IncomeStatementHeader
from decimal import Decimal

def main():
    db = SessionLocal()
    try:
        property_id = 11
        period_id = 169
        
        print("=" * 80)
        print("COVENANT COMPLIANCE VERIFICATION")
        print("=" * 80)
        print(f"Property: {property_id}, Period: {period_id}\n")
        
        # 1. DSCR (Debt Service Coverage Ratio)
        print("1. DSCR (Net Operating Income / Debt Service):")
        print("-" * 80)
        
        # Get NOI from Income Statement
        income_header = db.query(IncomeStatementHeader).filter(
            IncomeStatementHeader.property_id == property_id,
            IncomeStatementHeader.period_id == period_id
        ).first()
        
        noi = income_header.net_operating_income if income_header else Decimal('0')
        print(f"Net Operating Income (NOI): ${noi:,.2f}")
        
        # Get Debt Service from Mortgage Statement
        mortgage = db.query(MortgageStatementData).filter(
            MortgageStatementData.property_id == property_id,
            MortgageStatementData.period_id == period_id
        ).first()
        
        if mortgage:
            monthly_payment = mortgage.total_payment_due or Decimal('0')
            annual_debt_service = monthly_payment * 12
            print(f"Monthly Payment: ${monthly_payment:,.2f}")
            print(f"Annual Debt Service: ${annual_debt_service:,.2f}")
            
            if annual_debt_service > 0:
                dscr = float(noi / annual_debt_service)
                print(f"DSCR: {dscr:.2f}x")
            else:
                print("DSCR: N/A (no debt service)")
        else:
            print("No mortgage data found")
        
        # 2. LTV (Loan-to-Value Ratio)
        print("\n2. LTV (Loan Balance / Property Value):")
        print("-" * 80)
        
        if mortgage:
            loan_balance = mortgage.principal_balance or Decimal('0')
            print(f"Loan Balance: ${loan_balance:,.2f}")
        else:
            loan_balance = Decimal('0')
            print("Loan Balance: $0.00 (no mortgage data)")
        
        # Property value from... where?
        # Check balance sheet for property value or use acquisition cost
        property_value_accounts = db.query(BalanceSheetData).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.period_id == period_id,
            BalanceSheetData.account_code.like('15%')  # Fixed Assets
        ).all()
        
        property_value = sum(acc.amount for acc in property_value_accounts)
        print(f"Property Value (from Balance Sheet 15xx): ${property_value:,.2f}")
        
        if property_value > 0:
            ltv = float(loan_balance / property_value) * 100
            print(f"LTV: {ltv:.2f}%")
        else:
            print("LTV: 0.0% (no property value found)")
        
        # 3. ICR (Interest Coverage Ratio)
        print("\n3. ICR (NOI / Interest Expense):")
        print("-" * 80)
        
        if mortgage:
            # Use YTD interest which is the annual interest already
            interest_expense = mortgage.ytd_interest_paid or Decimal('0')
            print(f"YTD Interest Paid: ${interest_expense:,.2f}")
            
            if interest_expense > 0:
                icr = float(noi / interest_expense)
                print(f"ICR: {icr:.2f}x or {icr * 100:.2f}%")
            else:
                print("ICR: N/A (no interest expense)")
        
        # 4. Liquidity (Current Assets / Current Liabilities)
        print("\n4. LIQUIDITY (Current Assets / Current Liabilities):")
        print("-" * 80)
        
        current_assets = db.query(BalanceSheetData).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.period_id == period_id,
            BalanceSheetData.account_code.like('1%'),  # Assets
            BalanceSheetData.account_code < '1500'  # Current assets (< fixed assets)
        ).all()
        
        current_liabilities = db.query(BalanceSheetData).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.period_id == period_id,
            BalanceSheetData.account_code.like('2%'),  # Liabilities
            BalanceSheetData.account_code < '2500'  # Current liabilities
        ).all()
        
        total_current_assets = sum(acc.amount for acc in current_assets)
        total_current_liabilities = sum(abs(acc.amount) for acc in current_liabilities)
        
        print(f"Current Assets: ${total_current_assets:,.2f}")
        print(f"Current Liabilities: ${total_current_liabilities:,.2f}")
        
        if total_current_liabilities > 0:
            liquidity = float(total_current_assets / total_current_liabilities)
            print(f"Liquidity Ratio: {liquidity:.2f}x")
        else:
            print("Liquidity: N/A (no current liabilities)")

    except Exception as e:
        import traceback
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
