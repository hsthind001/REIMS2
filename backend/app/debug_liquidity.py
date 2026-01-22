"""
Debug Liquidity Calculation

Check why Current Assets and Current Liabilities are returning $0
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
        print("DEBUGGING LIQUIDITY RATIOS")
        print("=" * 80)
        print(f"Property: {property_id}, Period: {period_id}\n")
        
        # Test current query from service
        print("1. CURRENT QUERY (from covenant service):")
        print("-" * 80)
        
        current_query = text("""
            SELECT
                SUM(CASE WHEN account_category = 'ASSETS' AND account_subcategory ILIKE '%Current%' THEN amount ELSE 0 END) as current_assets,
                SUM(CASE WHEN account_category = 'LIABILITIES' AND account_subcategory ILIKE '%Current%' THEN amount ELSE 0 END) as current_liabilities,
                SUM(CASE WHEN account_name ILIKE '%INVENTORY%' THEN amount ELSE 0 END) as inventory
            FROM balance_sheet_data
            WHERE property_id = :property_id
            AND period_id = :period_id
        """)
        
        result = db.execute(current_query, {"property_id": property_id, "period_id": period_id})
        row = result.fetchone()
        
        print(f"Current Assets: ${float(row[0]) if row and row[0] else 0:,.2f}")
        print(f"Current Liabilities: ${float(row[1]) if row and row[1] else 0:,.2f}")
        print(f"Inventory: ${float(row[2]) if row and row[2] else 0:,.2f}")
        
        # Check what account categories and subcategories actually exist
        print("\n2. ACTUAL ACCOUNT CATEGORIES IN BALANCE SHEET:")
        print("-" * 80)
        
        categories_query = text("""
            SELECT DISTINCT account_category, account_subcategory, COUNT(*)
            FROM balance_sheet_data
            WHERE property_id = :property_id
            AND period_id = :period_id
            GROUP BY account_category, account_subcategory
            ORDER BY account_category, account_subcategory
        """)
        
        cat_result = db.execute(categories_query, {"property_id": property_id, "period_id": period_id})
        
        for row in cat_result:
            print(f"Category: {row[0]}, Subcategory: {row[1]}, Count: {row[2]}")
        
        # Check asset accounts by code
        print("\n3. ASSET ACCOUNTS (1xxxx codes):")
        print("-" * 80)
        
        assets_query = text("""
            SELECT account_code, account_name, amount, account_category, account_subcategory
            FROM balance_sheet_data
            WHERE property_id = :property_id
            AND period_id = :period_id
            AND account_code LIKE '1%'
            ORDER BY account_code
        """)
        
        assets_result = db.execute(assets_query, {"property_id": property_id, "period_id": period_id})
        
        total_current_assets = 0
        for row in assets_result:
            # Current assets are typically 11xx-14xx
            code = row[0]
            if code.startswith('11') or code.startswith('12') or code.startswith('13') or code.startswith('14'):
                total_current_assets += float(row[2])
                print(f"  {row[0]}: {row[1]} = ${float(row[2]):,.2f}")
        
        print(f"\nTotal Current Assets (11xx-14xx): ${total_current_assets:,.2f}")
        
        # Check liability accounts by code
        print("\n4. LIABILITY ACCOUNTS (2xxxx codes):")
        print("-" * 80)
        
        liabs_query = text("""
            SELECT account_code, account_name, amount, account_category, account_subcategory
            FROM balance_sheet_data
            WHERE property_id = :property_id
            AND period_id = :period_id
            AND account_code LIKE '2%'
            ORDER BY account_code
        """)
        
        liabs_result = db.execute(liabs_query, {"property_id": property_id, "period_id": period_id})
        
        total_current_liabs = 0
        for row in liabs_result:
            # Current liabilities are typically 20xx-21xx
            code = row[0]
            if code.startswith('20') or code.startswith('21'):
                total_current_liabs += abs(float(row[2]))
                print(f"  {row[0]}: {row[1]} = ${abs(float(row[2])):,.2f}")
        
        print(f"\nTotal Current Liabilities (20xx-21xx): ${total_current_liabs:,.2f}")
        
        # Calculate correct ratios
        if total_current_liabs > 0:
            current_ratio = total_current_assets / total_current_liabs
            quick_ratio = (total_current_assets - 0) / total_current_liabs  # Assuming no inventory
            print(f"\n5. CORRECT RATIOS:")
            print(f"Current Ratio: {current_ratio:.2f}x")
            print(f"Quick Ratio: {quick_ratio:.2f}x")

    except Exception as e:
        import traceback
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
