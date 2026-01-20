import sys
import os
from sqlalchemy import text

# Add backend directory to path
sys.path.append(os.getcwd())

from app.db.database import SessionLocal

def main():
    db = SessionLocal()
    try:
        # 1. Find Property
        print("--- PROPERTIES ---")
        result = db.execute(text("SELECT id, property_name FROM properties"))
        properties = result.fetchall()
        for p in properties:
            print(f"Property: {p.property_name} (ID: {p.id})")
        
        target_property = None
        if not properties:
            print("No properties found.")
            return

        # Try to find "Eastern" or "Plaza"
        for p in properties:
             if "Eastern" in p.property_name or "Plaza" in p.property_name:
                  target_property = p
                  break
        
        if not target_property:
             target_property = properties[0]
             print(f"Using fallback property: {target_property.property_name} (ID: {target_property.id})")
        else:
             print(f"Selected Property: {target_property.property_name} (ID: {target_property.id})")

        pid = target_property.id

        # 2. Find Period 2025-10
        print("\n--- PERIOD 2025-10 ---")
        period_query = text("SELECT id, period_year, period_month FROM financial_periods WHERE property_id = :pid AND period_year = 2025 AND period_month = 10")
        result = db.execute(period_query, {"pid": pid})
        period = result.fetchone()
        
        if not period:
            print("Period 2025-10 not found for this property.")
            return
        
        print(f"Period Found: {period.period_year}-{period.period_month} (ID: {period.id})")
        per_id = period.id

        # 3. Check Balance Sheet Data (Liabilities & Mortgage)
        print("\n--- BALANCE SHEET LIABILITIES / MORTGAGE ---")
        bs_query = text("""
            SELECT account_code, account_name, amount, account_category
            FROM balance_sheet_data 
            WHERE property_id = :pid AND period_id = :per_id
            AND (
                account_category ILIKE '%LIABIL%' 
                OR account_name ILIKE '%MORTGAGE%' 
                OR account_code ILIKE '%MORTGAGE%'
                OR account_name ILIKE '%LOAN%'
                OR account_name ILIKE '%DEBT%'
            )
            ORDER BY amount DESC
        """)
        rows = db.execute(bs_query, {"pid": pid, "per_id": per_id}).fetchall()

        if not rows:
            print("No liabilities/mortgage entries found in Balance Sheet data.")
        else:
            print(f"{'Code':<20} | {'Name':<40} | {'Amount':<15} | {'Category'}")
            print("-" * 100)
            for r in rows:
                print(f"{r.account_code:<20} | {r.account_name:<40} | {r.amount:<15} | {r.account_category}")

        # 4. Check Mortgage Statement Data (Cols)
        print("\n--- MORTGAGE STATEMENT DATA ---")
        # Get columns first
        cols_query = text("SELECT column_name FROM information_schema.columns WHERE table_name = 'mortgage_statement_data'")
        # Note: postgres specific information_schema
        try:
            cols = db.execute(cols_query).fetchall()
            print("Columns:", [c[0] for c in cols])
        except Exception as e:
            print("Could not fetch columns (sqlite?):", e)

        ms_query = text("""
            SELECT *
            FROM mortgage_statement_data
            WHERE property_id = :pid AND period_id = :per_id
        """)
        ms_rows = db.execute(ms_query, {"pid": pid, "per_id": per_id}).fetchall()
        if not ms_rows:
             print("No mortgage statement data found.")
        else:
             print(f"Found {len(ms_rows)} rows in mortgage_statement_data")
             for r in ms_rows:
                  print(r)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
