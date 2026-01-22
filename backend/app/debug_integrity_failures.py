import sys
from sqlalchemy import select, text
import json

# Add /app to path
sys.path.append('/app')

from app.db.database import SessionLocal
# detailed imports not strictly needed if we use raw SQL for quick inspection, 
# but let's try to be clean if possible. 
# actually raw SQL is faster for just dumping the table content.

def main():
    db = SessionLocal()
    try:
        property_id = 11
        period_id = 169
        
        print(f"Checking Validation Results for Property {property_id}, Period {period_id}...")
        
        # We need to find the active upload_id first, as validation_results links to upload_id
        # referencing the query in forensic_audit.py line 2085
        
        query = text("""
            SELECT 
                r.rule_name,
                r.rule_description,
                vr.passed,
                vr.actual_value,
                vr.expected_value,
                vr.difference,
                vr.error_message,
                vr.severity,
                du.document_type
            FROM validation_results vr
            JOIN validation_rules r ON r.id = vr.rule_id
            JOIN document_uploads du ON du.id = vr.upload_id
            WHERE du.property_id = :property_id
            AND du.period_id = :period_id
            AND du.is_active = true
            AND vr.passed = false
            ORDER BY du.document_type, r.rule_name
        """)
        
        results = db.execute(query, {"property_id": property_id, "period_id": period_id}).fetchall()
        
        if not results:
            print("No failures found or no active document uploads found.")
        else:
            print(f"Found {len(results)} failed validation checks:\n")
            current_doc_type = None
            for row in results:
                if row.document_type != current_doc_type:
                    print(f"\n--- {row.document_type} ---")
                    current_doc_type = row.document_type
                
                print(f"[{row.rule_name}] {row.rule_description}")
                print(f"  Result: {row.actual_value} | Expected: {row.expected_value} | Diff: {row.difference}")
                print(f"  Error: {row.error_message}")
                print(f"  Severity: {row.severity}")
                print("-" * 40)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
