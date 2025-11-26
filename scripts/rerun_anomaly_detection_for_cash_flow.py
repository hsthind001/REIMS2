"""
Re-run anomaly detection for existing cash flow documents.

This script finds all cash flow document uploads and re-runs anomaly detection
for them using the new absolute value threshold system.
"""

import os
import sys

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.models.financial_period import FinancialPeriod
from app.services.extraction_orchestrator import ExtractionOrchestrator
from app.services.anomaly_detector import StatisticalAnomalyDetector

def rerun_cash_flow_anomaly_detection(dry_run=True):
    """
    Re-run anomaly detection for all cash flow documents.
    
    Args:
        dry_run: If True, only report what would be done without actually running detection
    """
    db = SessionLocal()
    
    try:
        # Find all cash flow document uploads
        cash_flow_uploads = db.query(DocumentUpload).filter(
            DocumentUpload.document_type == 'cash_flow',
            DocumentUpload.extraction_status == 'completed'
        ).order_by(DocumentUpload.upload_date.desc()).all()
        
        print(f"Found {len(cash_flow_uploads)} cash flow document uploads")
        print(f"Mode: {'DRY RUN (no changes will be made)' if dry_run else 'RUNNING ANOMALY DETECTION'}")
        print("-" * 80)
        
        if not cash_flow_uploads:
            print("No cash flow documents found.")
            return
        
        orchestrator = ExtractionOrchestrator(db)
        
        for upload in cash_flow_uploads:
            # Get the period for this upload
            period = db.query(FinancialPeriod).filter(
                FinancialPeriod.id == upload.period_id
            ).first()
            
            if not period:
                print(f"⚠️  Upload {upload.id}: No period found, skipping")
                continue
            
            print(f"\n📄 Processing: {upload.file_name}")
            print(f"   Property ID: {upload.property_id}, Period: {period.period_year}/{period.period_month:02d}")
            
            if not dry_run:
                try:
                    # Initialize detector
                    detector = StatisticalAnomalyDetector(db)
                    
                    # Run anomaly detection
                    orchestrator._detect_cash_flow_anomalies(upload, period, detector)
                    
                    # Check how many anomalies were created
                    from sqlalchemy import text
                    anomaly_count = db.execute(
                        text("SELECT COUNT(*) FROM anomaly_detections WHERE document_id = :doc_id"),
                        {"doc_id": upload.id}
                    ).scalar()
                    
                    print(f"   ✅ Anomaly detection completed. {anomaly_count} anomalies found.")
                except Exception as e:
                    print(f"   ❌ Error: {str(e)}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"   [DRY RUN] Would run anomaly detection for this upload")
        
        if not dry_run:
            db.commit()
            print("\n✅ Anomaly detection completed for all cash flow documents!")
        else:
            print("\n⚠️  DRY RUN: No changes were made.")
            print("Run with --run flag to actually execute anomaly detection.")
        
    except Exception as e:
        db.rollback()
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Re-run anomaly detection for cash flow documents')
    parser.add_argument('--run', action='store_true', help='Actually run anomaly detection (default is dry run)')
    args = parser.parse_args()
    
    rerun_cash_flow_anomaly_detection(dry_run=not args.run)

