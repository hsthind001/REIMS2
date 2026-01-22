"""
Debug NOI Calculation in Covenant Compliance Service - Simplified

Check what values the NOI calculation is returning and why it's 26x too high.
"""
import sys
sys.path.append('/app')

from app.db.database import SessionLocal
from sqlalchemy import text

def main():
    db = SessionLocal()
    try:
        property_id = 11
        period_id = 169
        
        print("=" * 80)
        print("DEBUGGING NOI CALCULATION FOR DSCR")
        print("=" * 80)
        print(f"Property: {property_id}, Period: {period_id}\n")
        
        # Test Query: Calculate NOI from 4% and 5% accounts (same as service does)
        print("Calculate NOI from income (4%) and expenses (5%) accounts:")
        print("-" * 80)
        
        noi_query = text("""
            SELECT
                SUM(CASE WHEN account_code LIKE '4%' THEN period_amount ELSE 0 END) as total_income,
                SUM(CASE WHEN account_code LIKE '5%' THEN period_amount ELSE 0 END) as total_expenses
            FROM income_statement_data
            WHERE property_id = :property_id
            AND period_id = :period_id
        """)
        
        result = db.execute(noi_query, {"property_id": property_id, "period_id": period_id})
        row = result.fetchone()
        
        total_income = float(row[0]) if row and row[0] else 0
        total_expenses = float(row[1]) if row and row[1] else 0
        noi = total_income - total_expenses
        
        print(f"Total Income (4xxx): ${total_income:,.2f}")
        print(f"Total Expenses (5xxx): ${total_expenses:,.2f}")
        print(f"NOI: ${noi:,.2f}")
        
        # Check period type
        period_query = text("""
            SELECT period_start_date, period_end_date
            FROM financial_periods
            WHERE id = :period_id
        """)
        period_result = db.execute(period_query, {"period_id": period_id})
        period_row = period_result.fetchone()
        
        if period_row and period_row[0] and period_row[1]:
            period_days = (period_row[1] - period_row[0]).days + 1
            period_type = 'annual' if period_days >= 330 else 'monthly'
            print(f"\nPeriod: {period_row[0]} to {period_row[1]} ({period_days} days)")
            print(f"Period Type: {period_type}")
            
            if period_type == 'monthly':
                annual_noi = noi * 12
                print(f"Annualized NOI (x12): ${annual_noi:,.2f}")
            else:
                annual_noi = noi
                print(f"Annual NOI (no multiplication): ${annual_noi:,.2f}")
        
        # Compare to Income Statement Header
        print("\n" + "=" * 80)
        print("EXPECTED VALUES (from Income Statement Header):")
        print("=" * 80)
        
        header_query = text("""
            SELECT total_income, total_operating_expenses, net_operating_income
            FROM income_statement_headers
            WHERE property_id = :property_id
            AND period_id = :period_id
        """)
        header_result = db.execute(header_query, {"property_id": property_id, "period_id": period_id})
        header_row = header_result.fetchone()
        
        if header_row:
            print(f"Total Income: ${float(header_row[0]):,.2f}")
            print(f"Total Operating Expenses: ${float(header_row[1]):,.2f}")
            print(f"Net Operating Income: ${float(header_row[2]):,.2f}")
            print(f"Expected Annual NOI: ${float(header_row[2]) * 12:,.2f}")
        
        # Check detailed breakdown
        print("\n" + "=" * 80)
        print("DETAILED INCOME ACCOUNTS (first 10):")
        print("=" * 80)
        
        detail_query = text("""
            SELECT account_code, account_name, period_amount
            FROM income_statement_data
            WHERE property_id = :property_id
            AND period_id = :period_id
            AND account_code LIKE '4%'
            ORDER BY period_amount DESC
            LIMIT 10
        """)
        detail_result = db.execute(detail_query, {"property_id": property_id, "period_id": period_id})
        
        for row in detail_result:
            print(f"{row[0]}: {row[1]}: ${float(row[2]):,.2f}")

    except Exception as e:
        import traceback
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
