
import sys
import os
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import date

# Add backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.db.database import Base, get_db
from app.models.property import Property
from app.models.financial_metrics import FinancialMetrics
from app.models.financial_period import FinancialPeriod
from app.models.user import User
from app.models.organization import Organization

# Adjust database URL if needed - assuming default from env or config
# For this script we will try to use the dev database
DATABASE_URL = "postgresql://reims:reims@localhost:5433/reims" 

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def verify_cascade_delete():
    db = SessionLocal()
    try:
        print("Starting verification...")
        
        # 1. Get or Create a dummy organization and user for testing
        # We need these because of foreign Key constraints if they exist, 
        # or we might need them for context. 
        # For simplicity, let's just pick the first org and user
        org = db.query(Organization).first()
        user = db.query(User).first()
        
        if not org or not user:
            print("Error: Database must have at least one Organization and User.")
            return

        # 2. Create a Test Property
        test_property_code = "TESTDEL001"
        
        # Clean up if exists
        existing = db.query(Property).filter(Property.property_code == test_property_code).first()
        if existing:
            print(f"Cleaning up existing test property {test_property_code}...")
            db.delete(existing)
            db.commit()

        print(f"Creating test property {test_property_code}...")
        new_prop = Property(
            property_code=test_property_code,
            property_name="Test Deletion Property",
            organization_id=org.id,
            created_by=user.id,
            status='active'
        )
        db.add(new_prop)
        db.commit()
        db.refresh(new_prop)
        
        prop_id = new_prop.id
        print(f"Created Property ID: {prop_id}")

        # 2.5 Create Financial Period
        print("Creating Financial Period...")
        period = FinancialPeriod(
            property_id=prop_id,
            period_year=2024,
            period_month=1,
            period_start_date=date(2024, 1, 1),
            period_end_date=date(2024, 1, 31)
        )
        db.add(period)
        db.commit()
        db.refresh(period)
        period_id = period.id
        print(f"Created Financial Period ID: {period_id}")

        # 3. Create a related Financial Metric
        print("Creating related Financial Metric...")
        metric = FinancialMetrics(
            property_id=prop_id,
            period_id=period_id,
            total_revenue=10000.00,
            net_operating_income=5000.00
        )
        db.add(metric)
        db.commit()
        db.refresh(metric)
        
        metric_id = metric.id
        print(f"Created Financial Metric ID: {metric_id}")

        # 4. Verify they exist
        p_check = db.query(Property).filter(Property.id == prop_id).first()
        per_check = db.query(FinancialPeriod).filter(FinancialPeriod.id == period_id).first()
        m_check = db.query(FinancialMetrics).filter(FinancialMetrics.id == metric_id).first()
        
        if not p_check or not m_check or not per_check:
            print("Error: Setup failed, records not found.")
            return

        print("Setup successful. Records exist.")

        # 5. Delete the Property using SQLAlchemy session.delete
        # This mirrors what the API does.
        print("Deleting Property...")
        db.delete(p_check)
        db.commit()

        # 6. Verify Deletion
        print("Verifying Deletion...")
        p_deleted = db.query(Property).filter(Property.id == prop_id).first()
        per_deleted = db.query(FinancialPeriod).filter(FinancialPeriod.id == period_id).first()
        m_deleted = db.query(FinancialMetrics).filter(FinancialMetrics.id == metric_id).first()

        if p_deleted is None:
            print("SUCCESS: Property deleted.")
        else:
            print("FAILURE: Property still exists.")

        if per_deleted is None:
             print("SUCCESS: Related Financial Period deleted (Cascade worked).")
        else:
             print("FAILURE: Related Financial Period still exists (Cascade failed).")

        if m_deleted is None:
            print("SUCCESS: Related Financial Metric deleted (Cascade worked).")
        else:
            print("FAILURE: Related Financial Metric still exists (Cascade failed).")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    verify_cascade_delete()
