#!/usr/bin/env python3
"""
Test script to manually trigger alert evaluation for a property
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.services.alert_trigger_service import AlertTriggerService
from app.models.financial_metrics import FinancialMetrics

def test_alert_trigger(property_id: int, period_id: int):
    """Test alert trigger for a property/period"""
    db = SessionLocal()
    try:
        # Get metrics
        metrics = db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == property_id,
            FinancialMetrics.period_id == period_id
        ).first()
        
        if not metrics:
            print(f"❌ No metrics found for property {property_id}, period {period_id}")
            return False
        
        print(f"✅ Found metrics for property {property_id}, period {period_id}")
        print(f"   DSCR: {metrics.dscr}")
        print(f"   Occupancy Rate: {metrics.occupancy_rate}")
        print(f"   Operating Cash Flow: {metrics.operating_cash_flow}")
        
        # Trigger alerts
        alert_service = AlertTriggerService(db)
        created_alerts = alert_service.evaluate_and_trigger_alerts(
            property_id=property_id,
            period_id=period_id,
            metrics=metrics
        )
        
        print(f"\n✅ Triggered {len(created_alerts)} alert(s)")
        for alert in created_alerts:
            print(f"   - {alert.get('alert_type')}: {alert.get('title')} (Severity: {alert.get('severity')})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_alert_trigger.py <property_id> <period_id>")
        print("Example: python test_alert_trigger.py 1 13")
        sys.exit(1)
    
    property_id = int(sys.argv[1])
    period_id = int(sys.argv[2])
    
    success = test_alert_trigger(property_id, period_id)
    sys.exit(0 if success else 1)

