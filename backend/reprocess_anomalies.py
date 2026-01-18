
import sys
import os
import logging
from sqlalchemy import text

# Add app to path
sys.path.append(os.getcwd())

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.services.extraction_orchestrator import ExtractionOrchestrator

def reprocess_anomalies(property_id: int):
    db = SessionLocal()
    try:
        print(f"--- Reprocessing Anomalies for Property ID {property_id} ---")
        
        # Get all completed documents for this property
        uploads = db.query(DocumentUpload).filter(
            DocumentUpload.property_id == property_id,
            DocumentUpload.extraction_status == 'completed'
        ).all()
        
        if not uploads:
            print(f"No completed documents found for property {property_id}")
            return

        print(f"Found {len(uploads)} completed documents. Starting anomaly detection...")
        
        orchestrator = ExtractionOrchestrator(db)
        success_count = 0
        skip_count = 0
        fail_count = 0
        
        # Sort processing by period date (if possible) or upload date to maximize history availability
        # We don't have period date easily accessible without join, but ID roughly correlates with upload time.
        # However, for anomaly detection, we want to process in CHRONOLOGICAL order of the FINANCIAL PERIOD.
        # But `_detect_anomalies_for_document` just looks at DB history, so order of processing *now* doesn't matter 
        # as much as the fact that the history *exists* in the DB now. 
        # Actually, if we are generating anomalies, does it care about *previous anomalies*? No, just data.
        # Data is already in DB. So order doesn't matter.
        
        for upload in uploads:
            print(f"Processing Doc {upload.id} ({upload.file_name}) type={upload.document_type}...")
            
            # Skip unsupported types early to avoid log noise
            if upload.document_type not in ['income_statement', 'balance_sheet', 'cash_flow', 'rent_roll', 'mortgage_statement']:
                print(f"  Skipping unsupported type: {upload.document_type}")
                skip_count += 1
                continue
                
            try:
                orchestrator._detect_anomalies_for_document(upload)
                print(f"  ✅ Success")
                success_count += 1
            except ValueError as e:
                # Expected for insufficient history or validation
                print(f"  ⚠️  Skipped (Validation): {str(e)}")
                skip_count += 1
            except Exception as e:
                print(f"  ❌ Failed: {str(e)}")
                fail_count += 1

        print("-" * 30)
        print(f"Processing Complete.")
        print(f"Success: {success_count}")
        print(f"Skipped: {skip_count}")
        print(f"Failed:  {fail_count}")

    finally:
        db.close()

if __name__ == "__main__":
    reprocess_anomalies(11) # ESP001
