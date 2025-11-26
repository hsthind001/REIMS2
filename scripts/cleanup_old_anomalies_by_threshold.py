"""
Cleanup script to remove old anomalies that don't meet the new absolute value threshold criteria.

This script:
1. Gets all anomalies from the database
2. For each anomaly, calculates if it would meet the new absolute value threshold
3. Removes anomalies that don't meet the threshold (or marks them for review)
"""

import os
import sys
from decimal import Decimal

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.services.anomaly_threshold_service import AnomalyThresholdService

DATABASE_URL = settings.DATABASE_URL
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def cleanup_old_anomalies(dry_run=True, delete=False):
    """
    Clean up old anomalies that don't meet the new absolute value threshold.
    
    Args:
        dry_run: If True, only report what would be deleted without actually deleting
        delete: If True, actually delete the anomalies (only if dry_run is False)
    """
    db = SessionLocal()
    threshold_service = AnomalyThresholdService(db)
    default_threshold = float(threshold_service.get_default_threshold())
    
    try:
        # Get all anomalies
        anomalies = db.execute(text("""
            SELECT 
                ad.id,
                ad.document_id,
                ad.field_name,
                ad.field_value,
                ad.expected_value,
                ad.anomaly_type,
                ad.detected_at,
                du.document_type
            FROM anomaly_detections ad
            JOIN document_uploads du ON ad.document_id = du.id
            WHERE ad.anomaly_type = 'percentage_change'
            ORDER BY ad.detected_at DESC
        """)).fetchall()
        
        print(f"Found {len(anomalies)} anomalies with type 'percentage_change' (old system)")
        print(f"Default threshold: {default_threshold}")
        print(f"Mode: {'DRY RUN (no changes will be made)' if dry_run else 'DELETE MODE (anomalies will be deleted)'}")
        print("-" * 80)
        
        to_delete = []
        to_keep = []
        
        for anomaly in anomalies:
            anomaly_id, doc_id, field_name, field_value, expected_value, anomaly_type, detected_at, doc_type = anomaly
            
            try:
                # Parse values
                current_val = float(field_value) if field_value else 0
                expected_val = float(expected_value) if expected_value else 0
                
                # Calculate absolute difference
                absolute_difference = abs(current_val - expected_val)
                
                # Get threshold for this account (or use default)
                threshold = float(threshold_service.get_threshold_value(field_name))
                
                # Check if it meets the new threshold
                if absolute_difference <= threshold:
                    to_delete.append({
                        'id': anomaly_id,
                        'field_name': field_name,
                        'current': current_val,
                        'expected': expected_val,
                        'difference': absolute_difference,
                        'threshold': threshold,
                        'detected_at': detected_at
                    })
                else:
                    to_keep.append({
                        'id': anomaly_id,
                        'field_name': field_name,
                        'current': current_val,
                        'expected': expected_val,
                        'difference': absolute_difference,
                        'threshold': threshold
                    })
            except (ValueError, TypeError) as e:
                print(f"Error processing anomaly {anomaly_id}: {e}")
                continue
        
        print(f"\nAnomalies to DELETE (don't meet threshold): {len(to_delete)}")
        print(f"Anomalies to KEEP (meet threshold): {len(to_keep)}")
        print("-" * 80)
        
        if to_delete:
            print("\nTop 10 anomalies that would be deleted:")
            for i, anomaly in enumerate(to_delete[:10], 1):
                print(f"{i}. ID {anomaly['id']}: {anomaly['field_name']} - "
                      f"Diff: {anomaly['difference']:.2f}, Threshold: {anomaly['threshold']:.2f}, "
                      f"Detected: {anomaly['detected_at']}")
        
        if not dry_run and delete:
            if to_delete:
                anomaly_ids = [a['id'] for a in to_delete]
                deleted_count = db.execute(
                    text("DELETE FROM anomaly_detections WHERE id = ANY(:ids)"),
                    {"ids": anomaly_ids}
                ).rowcount
                db.commit()
                print(f"\n✅ Deleted {deleted_count} anomalies that don't meet the new threshold criteria.")
            else:
                print("\n✅ No anomalies to delete.")
        elif dry_run:
            print(f"\n⚠️  DRY RUN: {len(to_delete)} anomalies would be deleted.")
            print("Run with --delete flag to actually delete them.")
        
    except Exception as e:
        db.rollback()
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Clean up old anomalies that don\'t meet new threshold criteria')
    parser.add_argument('--delete', action='store_true', help='Actually delete anomalies (default is dry run)')
    args = parser.parse_args()
    
    cleanup_old_anomalies(dry_run=not args.delete, delete=args.delete)

