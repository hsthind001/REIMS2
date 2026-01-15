
import sys
import os
import random

# Add backend directory to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Mock settings if needed, but try to use existing environment
os.environ.setdefault("DATABASE_URL", "sqlite:///./backend/reims_app.db")

from sqlalchemy import text
from app.db.database import SessionLocal, engine
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.forensic_match import ForensicMatch
from app.models.forensic_reconciliation_session import ForensicReconciliationSession

def check_and_fix_coordinates():
    db = SessionLocal()
    try:
        print("Checking for existing coordinates...")
        bs_with_coords = db.query(BalanceSheetData).filter(BalanceSheetData.extraction_x0.isnot(None)).count()
        print(f"BalanceSheetData with coords: {bs_with_coords}")

        # if bs_with_coords == 0:
        print("Injecting dummy coordinates for testing...")
        
        # Get active session matches
        matches = db.query(ForensicMatch).limit(5).all()
        if not matches:
            print("No matches found to update.")
            return

        print(f"Found {len(matches)} matches. Updating their source/target records with dummy coordinates.")
        
        updated_count = 0
        for match in matches:
            # Update Source
            if match.source_document_type == 'balance_sheet':
                record = db.query(BalanceSheetData).filter(BalanceSheetData.id == match.source_record_id).first()
                if record:
                    record.extraction_x0 = 100.0
                    record.extraction_y0 = 100.0
                    record.extraction_x1 = 500.0
                    record.extraction_y1 = 200.0
                    record.page_number = 1
                    updated_count += 1
            
            # Update Target
            if match.target_document_type == 'income_statement':
                record = db.query(IncomeStatementData).filter(IncomeStatementData.id == match.target_record_id).first()
                if record:
                    record.extraction_x0 = 100.0
                    record.extraction_y0 = 300.0
                    record.extraction_x1 = 500.0
                    record.extraction_y1 = 400.0
                    record.page_number = 1
                    updated_count += 1
        
        db.commit()
        print(f"Updated {updated_count} records with dummy coordinates.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_and_fix_coordinates()
