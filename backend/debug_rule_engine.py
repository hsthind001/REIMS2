
import sys
import os
from sqlalchemy import text, inspect
from app.db.database import SessionLocal, engine
# from app.services.reconciliation_rule_engine import ReconciliationRuleEngine
from app.models.rent_roll_data import RentRollData

def debug_run():
    db = SessionLocal()
    try:
        # 1. Inspect Table Columns
        print("=== Checking Rent Roll Schema ===")
        inspector = inspect(engine)
        columns = [c['name'] for c in inspector.get_columns('rent_roll_data')]
        print(f"Columns in DB: {columns}")
        
        required = ['unit_area_sqft', 'occupancy_status', 'unit_number']
        for r in required:
            if r not in columns:
                print(f"❌ MISSING COLUMN: {r}")
            else:
                print(f"✅ Found column: {r}")

        # 2. Find a valid period
        print("\n=== Finding Valid Period ===")
        res = db.execute(text("SELECT id, property_id FROM financial_periods LIMIT 1"))
        row = res.fetchone()
        if not row:
            print("No financial periods found.")
            return
            
        period_id, prop_id = row
        print(f"Using Property {prop_id}, Period {period_id}")
        
        # 3. Run Engine
        print("\n=== Running Engine ===")
        # engine_svc = ReconciliationRuleEngine(db)
        # results = engine_svc.execute_all_rules(prop_id, period_id)
        results = []
        
        print(f"\nTotal Results: {len(results)}")
        
        # 4. Tally
        counts = {}
        for r in results:
            counts[r.category] = counts.get(r.category, 0) + 1
            if r.status == "FAIL" or "SYS" in r.rule_id:
                print(f"FAILURE: {r.rule_id} - {r.rule_name}: {r.details}")

        print("\n=== Summary Counts ===")
        for cat, count in counts.items():
            print(f"{cat}: {count}")

    except Exception as e:
        print(f"CRASH: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_run()
