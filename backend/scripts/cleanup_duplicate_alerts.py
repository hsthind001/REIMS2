"""
Cleanup Script: Remove Duplicate DSCR Alerts

This script identifies and removes duplicate DSCR alerts for the same property/period combination.
It keeps the most recent ACTIVE alert and marks others as RESOLVED with explanation.

Usage:
    python -m backend.scripts.cleanup_duplicate_alerts [--dry-run] [--property-id PROPERTY_ID]
"""
import sys
import os
from pathlib import Path

# Add project root to path (scripts are in /app/scripts, app is in /app)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import argparse
import logging

from app.db.database import SessionLocal
from app.models.committee_alert import CommitteeAlert, AlertType, AlertStatus
from app.models.financial_period import FinancialPeriod
from app.models.property import Property

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_duplicate_alerts(db: Session, property_id: int = None):
    """
    Find duplicate DSCR alerts grouped by property_id and financial_period_id
    """
    query = db.query(
        CommitteeAlert.property_id,
        CommitteeAlert.financial_period_id,
        func.count(CommitteeAlert.id).label('alert_count')
    ).filter(
        CommitteeAlert.alert_type == AlertType.DSCR_BREACH
    ).group_by(
        CommitteeAlert.property_id,
        CommitteeAlert.financial_period_id
    ).having(
        func.count(CommitteeAlert.id) > 1
    )
    
    if property_id:
        query = query.filter(CommitteeAlert.property_id == property_id)
    
    duplicates = query.all()
    
    result = []
    for prop_id, period_id, count in duplicates:
        # Get all alerts for this property/period
        alerts = db.query(CommitteeAlert).filter(
            CommitteeAlert.property_id == prop_id,
            CommitteeAlert.financial_period_id == period_id,
            CommitteeAlert.alert_type == AlertType.DSCR_BREACH
        ).order_by(
            CommitteeAlert.status == AlertStatus.ACTIVE,  # ACTIVE first
            CommitteeAlert.triggered_at.desc()  # Most recent first
        ).all()
        
        # Get property and period info
        property_obj = db.query(Property).filter(Property.id == prop_id).first()
        period = db.query(FinancialPeriod).filter(FinancialPeriod.id == period_id).first()
        
        result.append({
            "property_id": prop_id,
            "property_name": property_obj.property_name if property_obj else "Unknown",
            "property_code": property_obj.property_code if property_obj else "Unknown",
            "period_id": period_id,
            "period_info": {
                "year": period.period_year if period else None,
                "month": period.period_month if period else None,
            } if period else None,
            "alert_count": count,
            "alerts": [
                {
                    "id": alert.id,
                    "status": alert.status.value if alert.status else None,
                    "severity": alert.severity.value if alert.severity else None,
                    "actual_value": float(alert.actual_value) if alert.actual_value else None,
                    "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None,
                }
                for alert in alerts
            ]
        })
    
    return result


def cleanup_duplicates(db: Session, duplicates: list, dry_run: bool = True):
    """
    Clean up duplicate alerts by keeping the most recent ACTIVE alert
    and marking others as RESOLVED
    """
    total_resolved = 0
    total_deleted = 0
    
    for group in duplicates:
        alerts = group["alerts"]
        
        # Find the alert to keep (prefer ACTIVE, then most recent)
        alert_to_keep = None
        for alert_data in alerts:
            alert = db.query(CommitteeAlert).filter(CommitteeAlert.id == alert_data["id"]).first()
            if not alert:
                continue
            
            if alert.status == AlertStatus.ACTIVE:
                alert_to_keep = alert
                break
        
        # If no ACTIVE alert, keep the most recent one
        if not alert_to_keep:
            alert_to_keep = db.query(CommitteeAlert).filter(
                CommitteeAlert.id == alerts[0]["id"]
            ).first()
        
        if not alert_to_keep:
            continue
        
        period_str = f"{group['period_info']['year']}-{group['period_info']['month']:02d}" if group['period_info'] else 'Unknown'
        logger.info(
            f"Property: {group['property_name']} ({group['property_code']}), "
            f"Period: {period_str}, "
            f"Keeping alert {alert_to_keep.id} (status: {alert_to_keep.status.value})"
        )
        
        # Mark other alerts as RESOLVED
        for alert_data in alerts:
            if alert_data["id"] == alert_to_keep.id:
                continue
            
            alert = db.query(CommitteeAlert).filter(CommitteeAlert.id == alert_data["id"]).first()
            if not alert:
                continue
            
            if dry_run:
                logger.info(
                    f"  [DRY RUN] Would resolve alert {alert.id} "
                    f"(status: {alert.status.value if alert.status else 'None'})"
                )
            else:
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.utcnow()
                alert.resolved_by = None
                alert.resolution_notes = (
                    f"Duplicate removed: Kept alert {alert_to_keep.id} for same property/period. "
                    f"Original status: {alert.status.value if alert.status else 'Unknown'}"
                )
                total_resolved += 1
                logger.info(f"  Resolved alert {alert.id}")
        
        if not dry_run:
            db.commit()
    
    return {
        "total_resolved": total_resolved,
        "total_deleted": total_deleted,
        "dry_run": dry_run
    }


def main():
    parser = argparse.ArgumentParser(description="Cleanup duplicate DSCR alerts")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--property-id",
        type=int,
        help="Limit cleanup to specific property ID"
    )
    
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        logger.info("🔍 Searching for duplicate DSCR alerts...")
        duplicates = find_duplicate_alerts(db, property_id=args.property_id)
        
        if not duplicates:
            logger.info("✅ No duplicate alerts found!")
            return
        
        logger.info(f"📊 Found {len(duplicates)} property/period combinations with duplicates:")
        for group in duplicates:
            period_str = f"{group['period_info']['year']}-{group['period_info']['month']:02d}" if group['period_info'] else 'Unknown'
            logger.info(
                f"  - {group['property_name']} ({group['property_code']}): "
                f"{group['alert_count']} alerts for period {period_str}"
            )
        
        if args.dry_run:
            logger.info("\n🔍 DRY RUN MODE - No changes will be made\n")
        else:
            logger.info("\n⚠️  LIVE MODE - Changes will be committed to database\n")
            response = input("Continue? (yes/no): ")
            if response.lower() != "yes":
                logger.info("Aborted.")
                return
        
        result = cleanup_duplicates(db, duplicates, dry_run=args.dry_run)
        
        if args.dry_run:
            logger.info(f"\n✅ DRY RUN complete. Would resolve {len([a for g in duplicates for a in g['alerts']]) - len(duplicates)} alerts")
        else:
            logger.info(f"\n✅ Cleanup complete. Resolved {result['total_resolved']} duplicate alerts")
            
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {str(e)}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()

