
import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.db.database import Base, get_db
from app.models.property import Property
from app.models.financial_metrics import FinancialMetrics
from app.models.financial_period import FinancialPeriod
from app.models.committee_alert import CommitteeAlert

# Adjust database URL
DATABASE_URL = "postgresql://reims:reims@localhost:5433/reims" 

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def cleanup_properties():
    db = SessionLocal()
    try:
        print("Starting cleanup of hidden properties...")
        
        # We identified these IDs in the previous step
        target_ids = [1, 2, 3, 4, 5]
        
        properties = db.query(Property).filter(Property.id.in_(target_ids)).all()
        
        if not properties:
            print("No properties found with the target IDs.")
            return

        print(f"Found {len(properties)} properties to delete.")
        
        for prop in properties:
            print(f"Deleting Property: {prop.property_name} (Code: {prop.property_code}, ID: {prop.id})...")
            # This ORM delete should now trigger cascading deletes for related records
            # because we removed lazy="noload" in the model definition.
            db.delete(prop)
        
        db.commit()
        print("Deletion committed successfully.")
        
        # Verify cleanup
        print("\nVerifying cleanup...")
        remaining_props = db.query(Property).count()
        remaining_metrics = db.query(FinancialMetrics).count()
        remaining_alerts = db.query(CommitteeAlert).count()
        
        print(f"Remaining Properties: {remaining_props}")
        print(f"Remaining Financial Metrics: {remaining_metrics}")
        print(f"Remaining Committee Alerts: {remaining_alerts}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_properties()
