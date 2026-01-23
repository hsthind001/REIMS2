import sys
import os

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.db.database import SessionLocal
from app.services.reconciliation_rule_engine import ReconciliationRuleEngine

def test_rule_execution():
    print("Initializing DB Session...")
    db = SessionLocal()
    
    try:
        print("Initializing ReconciliationRuleEngine...")
        engine = ReconciliationRuleEngine(db)
        
        PROPERTY_ID = 11
        PERIOD_ID = 169
        
        print(f"Executing Rules for Property {PROPERTY_ID}, Period {PERIOD_ID}...")
        
        # Synchronous execution
        results = engine.execute_all_rules(PROPERTY_ID, PERIOD_ID)
        
        print(f"\nExecution Complete. Found {len(results)} results.")
        
        passed = [r for r in results if r.status == "PASS"]
        failed = [r for r in results if r.status == "FAIL"]
        warnings = [r for r in results if r.status == "WARNING"]
        skipped = [r for r in results if r.status == "SKIP"]
        
        print(f"PASS: {len(passed)}")
        print(f"FAIL: {len(failed)}")
        print(f"WARNING: {len(warnings)}")
        print(f"SKIP: {len(skipped)}")
        
        print("\n--- SAMPLE FAILURES ---")
        for f in failed[:5]:
            print(f"[FAIL] {f.rule_name}: {f.details} (Diff: {f.difference})")
            
        print("\n--- SAMPLE WARNINGS ---")
        for w in warnings[:5]:
            print(f"[WARN] {w.rule_name}: {w.details}")
            
        print("\n--- SAMPLE PASS ---")
        for p in passed[:3]:
            print(f"[PASS] {p.rule_name}: {p.details}")

        print("\nSaving results to database...")
        engine.save_results()
        print("Results saved.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_rule_execution()
