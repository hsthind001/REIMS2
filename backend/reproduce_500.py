import sys
import os
import logging
import traceback

# Add backend directory to sys.path
sys.path.append('/home/hsthind/Documents/GitHub/REIMS2/backend')

from app.db.database import SessionLocal
from app.services.forensic_reconciliation_service import ForensicReconciliationService

# Configure logging to show everything
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def reproduce():
    print("Script starting...")
    try:
        db = SessionLocal()
        print("DB Session created.")
        
        print("Initializing ForensicReconciliationService...")
        service = ForensicReconciliationService(db)
        print("Service initialized successfully.")
        
        # Try a call that failed for the user
        # 11 and 147 
        property_id = 11
        period_id = 147
        
        print(f"Calling check_data_availability({property_id}, {period_id})...")
        try:
            result = service.check_data_availability(property_id, period_id)
            print("Result success!")
            # print(result)
        except Exception as e:
            print(f"Error checking availability: {e}")
            traceback.print_exc()

        print(f"Calling get_reconciliation_dashboard({property_id}, {period_id})...")
        try:
            result_dash = service.get_reconciliation_dashboard(property_id, period_id)
            print("Dashboard Result success!")
            # print(result_dash)
        except Exception as e:
            print(f"Error checking dashboard: {e}")
            traceback.print_exc()

    except Exception as e:
        print(f"Initialization Error: {e}")
        traceback.print_exc()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    reproduce()
