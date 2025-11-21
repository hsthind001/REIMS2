#!/usr/bin/env python3
"""
Recalculate all DSCR alerts for all properties to ensure accuracy.
This script will:
1. Recalculate DSCR for all properties
2. Update existing alerts with correct values
3. Auto-resolve alerts that are now healthy
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.property import Property
from app.services.dscr_monitoring_service import DSCRMonitoringService
from app.models.committee_alert import CommitteeAlert, AlertType, AlertStatus

def recalculate_all_dscr_alerts():
    """Recalculate DSCR for all properties and update alerts"""
    db: Session = SessionLocal()
    try:
        dscr_service = DSCRMonitoringService(db)
        
        # Get all active properties
        properties = db.query(Property).filter(Property.status == 'active').all()
        
        print(f"Found {len(properties)} active properties")
        print("=" * 80)
        
        for property in properties:
            print(f"\nProcessing {property.property_code} - {property.property_name}...")
            
            try:
                # Calculate DSCR (this will update/create alerts automatically)
                result = dscr_service.calculate_dscr(property.id)
                
                if result.get("success"):
                    dscr = result.get("dscr")
                    status = result.get("status")
                    print(f"  ✓ DSCR: {dscr:.4f} ({status})")
                    
                    if result.get("alert_created"):
                        print(f"  ✓ Alert created/updated")
                    if result.get("alerts_resolved"):
                        print(f"  ✓ {result.get('alerts_resolved')} alert(s) auto-resolved")
                else:
                    print(f"  ✗ Error: {result.get('error')}")
                    
            except Exception as e:
                print(f"  ✗ Failed: {str(e)}")
                continue
        
        print("\n" + "=" * 80)
        print("Recalculation complete!")
        
        # Show summary
        total_alerts = db.query(CommitteeAlert).filter(
            CommitteeAlert.alert_type == AlertType.DSCR_BREACH
        ).count()
        active_alerts = db.query(CommitteeAlert).filter(
            CommitteeAlert.alert_type == AlertType.DSCR_BREACH,
            CommitteeAlert.status == AlertStatus.ACTIVE
        ).count()
        resolved_alerts = db.query(CommitteeAlert).filter(
            CommitteeAlert.alert_type == AlertType.DSCR_BREACH,
            CommitteeAlert.status == AlertStatus.RESOLVED
        ).count()
        
        print(f"\nSummary:")
        print(f"  Total DSCR Alerts: {total_alerts}")
        print(f"  Active Alerts: {active_alerts}")
        print(f"  Resolved Alerts: {resolved_alerts}")
        
    finally:
        db.close()

if __name__ == "__main__":
    recalculate_all_dscr_alerts()

