"""
Investigate LTV Data Sources

Find:
1. Actual mortgage balance account code in Balance Sheet
2. Property value sources (purchase price, appraisal, or balance sheet)
3. Fix the LTV query
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
        print("INVESTIGATING LTV DATA SOURCES")
        print("=" * 80)
        print(f"Property: {property_id}, Period: {period_id}\n")
        
        # 1. Find Mortgage Balance in Balance Sheet
        print("1. SEARCHING FOR MORTGAGE BALANCE IN BALANCE SHEET:")
        print("-" * 80)
        
        # Check all liability accounts (2xxxx)
        mortgage_search = text("""
            SELECT account_code, account_name, amount, account_category, account_subcategory
            FROM balance_sheet_data
            WHERE property_id = :property_id
            AND period_id = :period_id
            AND account_code LIKE '2%'
            AND (
                account_name ILIKE '%mortgage%' 
                OR account_name ILIKE '%loan%'
                OR account_name ILIKE '%note%payable%'
                OR account_code LIKE '21%'
                OR account_code LIKE '22%'
            )
            ORDER BY ABS(amount) DESC
        """)
        
        result = db.execute(mortgage_search, {"property_id": property_id, "period_id": period_id})
        rows = result.fetchall()
        
        if rows:
            print(f"Found {len(rows)} potential mortgage accounts:")
            for row in rows:
                print(f"  {row[0]}: {row[1]}")
                print(f"    Amount: ${abs(float(row[2])):,.2f}")
                print(f"    Category: {row[3]}, Subcategory: {row[4]}")
        else:
            print("❌ No mortgage accounts found in Balance Sheet!")
        
        # 2. Check Mortgage Statement Data
        print("\n2. MORTGAGE STATEMENT DATA:")
        print("-" * 80)
        
        mortgage_stmt = text("""
            SELECT loan_number, principal_balance, total_loan_balance, lender_id
            FROM mortgage_statement_data
            WHERE property_id = :property_id
            AND period_id = :period_id
        """)
        
        stmt_result = db.execute(mortgage_stmt, {"property_id": property_id, "period_id": period_id})
        stmt_row = stmt_result.fetchone()
        
        if stmt_row:
            print(f"Loan Number: {stmt_row[0]}")
            print(f"Principal Balance: ${float(stmt_row[1]):,.2f}")
            print(f"Total Loan Balance: ${float(stmt_row[2]) if stmt_row[2] else 0:,.2f}")
            print(f"Lender ID: {stmt_row[3]}")
        else:
            print("❌ No mortgage statement data found!")
        
        # 3. Check Property Value Sources
        print("\n3. PROPERTY VALUE SOURCES:")
        print("-" * 80)
        
        # Check properties table
        property_query = text("""
            SELECT 
                purchase_price,
                acquisition_costs,
                current_value,
                assessed_value
            FROM properties
            WHERE id = :property_id
        """)
        
        prop_result = db.execute(property_query, {"property_id": property_id})
        prop_row = prop_result.fetchone()
        
        if prop_row:
            print("From properties table:")
            print(f"  Purchase Price: ${float(prop_row[0]) if prop_row[0] else 0:,.2f}")
            print(f"  Acquisition Costs: ${float(prop_row[1]) if prop_row[1] else 0:,.2f}")
            print(f"  Current Value: ${float(prop_row[2]) if prop_row[2] else 0:,.2f}")
            print(f"  Assessed Value: ${float(prop_row[3]) if prop_row[3] else 0:,.2f}")
        
        # Check Balance Sheet for Fixed Assets
        fixed_assets = text("""
            SELECT account_code, account_name, amount
            FROM balance_sheet_data
            WHERE property_id = :property_id
            AND period_id = :period_id
            AND (
                account_code LIKE '15%'
                OR account_code LIKE '16%'
                OR account_name ILIKE '%building%'
                OR account_name ILIKE '%land%'
                OR account_name ILIKE '%property%'
            )
            ORDER BY amount DESC
        """)
        
        assets_result = db.execute(fixed_assets, {"property_id": property_id, "period_id": period_id})
        assets_rows = assets_result.fetchall()
        
        if assets_rows:
            print("\nFrom Balance Sheet (Fixed Assets):")
            total_assets = 0
            for row in assets_rows:
                print(f"  {row[0]}: {row[1]} = ${float(row[2]):,.2f}")
                total_assets += float(row[2])
            print(f"  TOTAL Fixed Assets: ${total_assets:,.2f}")
        
        # 4. Recommendation
        print("\n" + "=" * 80)
        print("RECOMMENDATION FOR LTV CALCULATION:")
        print("=" * 80)
        
        if stmt_row:
            print(f"✅ Use Mortgage Statement principal_balance: ${float(stmt_row[1]):,.2f}")
        elif rows:
            print(f"✅ Use Balance Sheet mortgage account: ${abs(float(rows[0][2])):,.2f}")
        
        if prop_row and prop_row[0]:
            total_value = float(prop_row[0]) + (float(prop_row[1]) if prop_row[1] else 0)
            print(f"✅ Use purchase_price + acquisition_costs: ${total_value:,.2f}")
        elif prop_row and prop_row[2]:
            print(f"✅ Use current_value: ${float(prop_row[2]):,.2f}")
        elif assets_rows:
            print(f"⚠️ Use Fixed Assets total: ${total_assets:,.2f} (not ideal)")

    except Exception as e:
        import traceback
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
