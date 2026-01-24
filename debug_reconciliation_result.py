
import sys
import os

# Add backend directory to sys.path so we can import app modules
params = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.append(params)

try:
    from app.services.reconciliation_types import ReconciliationResult
    print("Successfully imported ReconciliationResult")
    
    try:
        res = ReconciliationResult(
            rule_id="TEST-1",
            rule_name="Test Rule",
            category="Test",
            status="PASS",
            source_value=100.0,
            target_value=100.0,
            difference=0.0,
            variance_pct=0.0,
            details="Test Details",
            severity="low",
            formula="Test Formula"
        )
        print(f"Successfully instantiated ReconciliationResult: {res}")
        if hasattr(res, 'formula'):
             print(f"Result has formula: {res.formula}")
        else:
             print("Result DOES NOT have formula attribute!")

    except Exception as e:
        print(f"Failed to instantiate ReconciliationResult: {e}")

except ImportError as e:
    print(f"Failed to import: {e}")
