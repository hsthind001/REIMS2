"""
Test Financial Integrity Hub API Endpoints

Check what data is returned for the dashboard
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
        print("TESTING FINANCIAL INTEGRITY HUB DATA")
        print("=" * 80)
        print(f"Property: {property_id}, Period: {period_id}\n")
        
        # 1. Check Cross-Document Reconciliations
        print("1. CROSS-DOCUMENT RECONCILIATIONS:")
        print("-" * 80)
        
        recon_query = text("""
            SELECT 
                reconciliation_type,
                status,
                expected_value,
                actual_value,
                variance_amount,
                variance_pct
            FROM cross_document_reconciliations
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
        """)
        
        result = db.execute(recon_query, {"property_id": property_id, "period_id": period_id})
        rows = result.fetchall()
        
        if rows:
            print(f"Found {len(rows)} reconciliations:")
            for row in rows:
                print(f"\n  Type: {row[0]}")
                print(f"  Status: {row[1]}")
                print(f"  Expected: ${float(row[2]) if row[2] else 0:,.2f}")
                print(f"  Actual: ${float(row[3]) if row[3] else 0:,.2f}")
                print(f"  Variance: ${float(row[4]) if row[4] else 0:,.2f} ({float(row[5]) if row[5] else 0:.2f}%)")
        else:
            print("❌ NO reconciliations found!")
        
        # 2. Check Validation Results
        print("\n2. VALIDATION RESULTS:")
        print("-" * 80)
        
        val_query = text("""
            SELECT 
                rule_type,
                rule_code,
                passing_tests,
                total_tests,
                status
            FROM validation_results
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY last_run DESC
            LIMIT 10
        """)
        
        val_result = db.execute(val_query, {"property_id": property_id, "period_id": period_id})
        val_rows = val_result.fetchall()
        
        if val_rows:
            print(f"Found {len(val_rows)} validation results:")
            for row in val_rows:
                print(f"  {row[1]}: {row[2]}/{row[3]} passing ({row[4]})")
        else:
            print("❌ NO validation results found!")
       
        # 3. Check if reconciliation service has been run
        print("\n3. RECONCILIATION SERVICE EXECUTION:")
        print("-" * 80)
        
        # Check if there are validation caches (Mathematical Integrity)
        cache_query = text("""
           SELECT COUNT(*)
            FROM validation_results_cache
            WHERE property_id = :property_id
            AND period_id = :period_id
        """)
        
        cache_result = db.execute(cache_query, {"property_id": property_id, "period_id": period_id})
        cache_count = cache_result.scalar()
        
        print(f"Validation cache entries: {cache_count}")
        
        # 4. Check Audit Scorecard
        print("\n4. AUDIT SCORECARD SUMMARY:")
        print("-" * 80)
        
        scorecard_query = text("""
            SELECT 
                overall_score,
                total_rules,
                passed_rules,
                failed_rules
            FROM audit_scorecard_summaries
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        sc_result = db.execute(scorecard_query, {"property_id": property_id, "period_id": period_id})
        sc_row = sc_result.fetchone()
        
        if sc_row:
            print(f"Overall Score: {float(sc_row[0]):.1f}%")
            print(f"Passed Rules: {sc_row[2]}/{sc_row[1]}")
            print(f"Failed Rules: {sc_row[3]}")
        else:
            print("❌ NO audit scorecard found!")
        
        # 5. Summary
        print("\n" + "=" * 80)
        print("DIAGNOSIS:")
        print("=" * 80)
        
        if not rows:
            print("❌ Cross-document reconciliations have NOT been run for this property/period")
            print("   → This is why Reconciliation Matrix is empty")
        
        if not val_rows:
            print("❌ Validation rules have NOT been executed")
            print("   → This is why Integrity Score shows N/A")
        
        if not sc_row:
            print("❌ Audit scorecard has NOT been generated")
            print("   → Dashboard needs forensic audit to be run")
        
        print("\nRECOMMENDATION:")
        print("Run the forensic audit/reconciliation service to populate dashboard data")

    except Exception as e:
        import traceback
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
