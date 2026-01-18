
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

def debug_anomaly_detection(document_id: int):
    db = SessionLocal()
    try:
        print(f"--- Debugging Anomaly Detection for Document ID {document_id} ---")
        
        upload = db.query(DocumentUpload).filter(DocumentUpload.id == document_id).first()
        if not upload:
            print(f"Document {document_id} not found")
            return

        print(f"Document: {upload.file_name}")
        print(f"Type: {upload.document_type}")
        print(f"Period ID: {upload.period_id}")
        print(f"Property ID: {upload.property_id}")
        print(f"Status: {upload.extraction_status}")

        orchestrator = ExtractionOrchestrator(db)
        
        try:
            print("Calling _detect_anomalies_for_document...")
            orchestrator._detect_anomalies_for_document(upload)
            print("SUCCESS: Anomaly detection completed without error.")
        except Exception as e:
            print(f"FAILURE: Anomaly detection failed with error:")
            print(str(e))
            import traceback
            traceback.print_exc()

    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        doc_id = int(sys.argv[1])
    else:
        doc_id = 350 # Default to Jan 2025 Income Statement if available
    
    debug_anomaly_detection(doc_id)
