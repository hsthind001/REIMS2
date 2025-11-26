"""
Re-run anomaly detection for balance sheet documents.
Run this from the backend directory: python3 scripts/rerun_balance_sheet_anomalies.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.models.financial_period import FinancialPeriod
from app.services.extraction_orchestrator import ExtractionOrchestrator
from app.services.anomaly_detector import StatisticalAnomalyDetector
from sqlalchemy import text

def rerun_balance_sheet_anomaly_detection():
    """Re-run anomaly detection for all balance sheet documents."""
    db = SessionLocal()
    
    try:
        # Find all balance sheet document uploads
        balance_sheet_uploads = db.query(DocumentUpload).filter(
            DocumentUpload.document_type == 'balance_sheet',
            DocumentUpload.extraction_status == 'completed'
        ).order_by(DocumentUpload.upload_date.desc()).all()
        
        print(f"Found {len(balance_sheet_uploads)} balance sheet document uploads")
        print("-" * 80)
        
        if not balance_sheet_uploads:
            print("No balance sheet documents found.")
            return
        
        orchestrator = ExtractionOrchestrator(db)
        
        for upload in balance_sheet_uploads:
            # Get the period for this upload
            period = db.query(FinancialPeriod).filter(
                FinancialPeriod.id == upload.period_id
            ).first()
            
            if not period:
                print(f"⚠️  Upload {upload.id}: No period found, skipping")
                continue
            
            print(f"\n📄 Processing: {upload.file_name}")
            print(f"   Property ID: {upload.property_id}, Period: {period.period_year}/{period.period_month:02d}")
            
            try:
                # Delete existing anomalies for this upload
                deleted_count = db.execute(
                    text("DELETE FROM anomaly_detections WHERE document_id = :doc_id"),
                    {"doc_id": upload.id}
                ).rowcount
                db.commit()
                print(f"   Deleted {deleted_count} old anomalies")
                
                # Initialize detector
                detector = StatisticalAnomalyDetector(db)
                
                # Run anomaly detection
                orchestrator._detect_balance_sheet_anomalies(upload, period, detector)
                db.commit()
                
                # Check how many anomalies were created
                anomaly_count = db.execute(
                    text("SELECT COUNT(*) FROM anomaly_detections WHERE document_id = :doc_id"),
                    {"doc_id": upload.id}
                ).scalar()
                
                print(f"   ✅ Anomaly detection completed. {anomaly_count} anomalies detected.")
            except Exception as e:
                db.rollback()
                print(f"   ❌ Error: {str(e)}")
                import traceback
                traceback.print_exc()
        
        print("\n✅ Anomaly detection completed for all balance sheet documents!")
        
    except Exception as e:
        db.rollback()
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    rerun_balance_sheet_anomaly_detection()

