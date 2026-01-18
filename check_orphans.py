
import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Adjust database URL
DATABASE_URL = "postgresql://reims:reims@localhost:5433/reims" 

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_orphans():
    db = SessionLocal()
    try:
        print("Checking for orphaned data...")
        
        # Get all valid property IDs
        valid_property_ids = [r[0] for r in db.execute(text("SELECT id FROM properties")).fetchall()]
        print(f"Valid Property IDs: {valid_property_ids}")
        
        if not valid_property_ids:
            print("No properties exist. Any data in related tables is orphaned.")
            valid_ids_str = "(NULL)" # Just to prevent SQL syntax errors in NOT IN (NULL)
        else:
            valid_ids_str = ",".join(map(str, valid_property_ids))

        # Tables to check that have property_id
        tables = [
            "financial_metrics",
            "financial_periods",
            "committee_alerts",
            "document_uploads",
            "workflow_locks",
            "tenant_recommendations",
            "property_research",
            "market_intelligence"
        ]

        total_orphans = 0

        for table in tables:
            query = text(f"SELECT COUNT(*) FROM {table} WHERE property_id NOT IN (SELECT id FROM properties)")
            # If valid_property_ids is empty, the subquery SELECT id FROM properties returns nothing, so NOT IN works correctly or we need to handle empty set carefully.
            # Actually standard SQL: x NOT IN (empty set) is True.
            
            count = db.execute(query).scalar()
            if count > 0:
                print(f"FOUND ORPHANS: Table '{table}' has {count} orphaned records.")
                total_orphans += count
            else:
                print(f"Table '{table}' is clean.")
        
        # New: Inspect the existing properties
        print("\n--- Insight into Existing Properties ---")
        param_ids = tuple(valid_property_ids) if valid_property_ids else (None,)
        # Handing case where tuple has only 1 element requires trailing comma which python generic tuple repr handles, 
        # but SQL might need care. Using simple loop/query for clarity.
        
        props = db.execute(text("SELECT id, property_code, property_name, status, organization_id FROM properties")).fetchall()
        for p in props:
            print(f"ID: {p[0]}, Code: {p[1]}, Name: {p[2]}, Status: {p[3]}, OrgID: {p[4]}")

        if total_orphans > 0:
            print(f"\nTotal Orphans Found: {total_orphans}")
            print("Recommendation: Run cleanup script.")
        else:
            print("\nNo orphaned data found directly linked to properties.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_orphans()
