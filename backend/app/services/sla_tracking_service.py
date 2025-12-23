"""
SLA Tracking Service

Calculates SLA due times and tracks MTTA and MTTR metrics.
"""

from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import logging

from app.models.committee_alert import CommitteeAlert, AlertSeverity, AlertStatus

logger = logging.getLogger(__name__)


class SLATrackingService:
    """
    Tracks SLA compliance and calculates MTTA/MTTR metrics.
    
    SLA Timeframes:
    - URGENT: 1 hour
    - CRITICAL: 4 hours
    - WARNING: 24 hours
    - INFO: 72 hours
    """
    
    def __init__(self, db: Session):
        """Initialize SLA tracking service."""
        self.db = db
        
        # SLA timeframes by severity
        self.sla_timeframes = {
            AlertSeverity.URGENT: timedelta(hours=1),
            AlertSeverity.CRITICAL: timedelta(hours=4),
            AlertSeverity.WARNING: timedelta(hours=24),
            AlertSeverity.INFO: timedelta(hours=72)
        }
    
    def calculate_sla_due_at(
        self,
        alert: CommitteeAlert
    ) -> Optional[datetime]:
        """
        Calculate SLA due time for an alert.
        
        Args:
            alert: CommitteeAlert record
            
        Returns:
            SLA due datetime
        """
        if not alert.created_at:
            return None
        
        timeframe = self.sla_timeframes.get(alert.severity)
        if not timeframe:
            return None
        
        return alert.created_at + timeframe
    
    def update_alert_sla(
        self,
        alert_id: int
    ) -> bool:
        """
        Update alert with SLA due time.
        
        Args:
            alert_id: CommitteeAlert ID
            
        Returns:
            True if updated successfully
        """
        alert = self.db.query(CommitteeAlert).filter(
            CommitteeAlert.id == alert_id
        ).first()
        
        if not alert:
            return False
        
        alert.sla_due_at = self.calculate_sla_due_at(alert)
        self.db.commit()
        
        return True
    
    def track_acknowledgment(
        self,
        alert_id: int,
        acknowledged_at: datetime
    ) -> bool:
        """
        Track alert acknowledgment and calculate MTTA.
        
        Args:
            alert_id: CommitteeAlert ID
            acknowledged_at: When alert was acknowledged
            
        Returns:
            True if tracked successfully
        """
        alert = self.db.query(CommitteeAlert).filter(
            CommitteeAlert.id == alert_id
        ).first()
        
        if not alert or not alert.created_at:
            return False
        
        # Calculate MTTA (Mean Time To Acknowledge)
        mtta_seconds = (acknowledged_at - alert.created_at).total_seconds()
        alert.mtta = int(mtta_seconds / 60)  # Store in minutes
        
        self.db.commit()
        
        return True
    
    def track_resolution(
        self,
        alert_id: int,
        resolved_at: datetime
    ) -> bool:
        """
        Track alert resolution and calculate MTTR.
        
        Args:
            alert_id: CommitteeAlert ID
            resolved_at: When alert was resolved
            
        Returns:
            True if tracked successfully
        """
        alert = self.db.query(CommitteeAlert).filter(
            CommitteeAlert.id == alert_id
        ).first()
        
        if not alert or not alert.created_at:
            return False
        
        # Calculate MTTR (Mean Time To Resolve)
        mttr_seconds = (resolved_at - alert.created_at).total_seconds()
        alert.mttr = int(mttr_seconds / 60)  # Store in minutes
        
        alert.status = AlertStatus.RESOLVED
        self.db.commit()
        
        return True
    
    def get_sla_metrics(
        self,
        property_id: Optional[int] = None,
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get SLA compliance metrics.
        
        Args:
            property_id: Optional property filter
            lookback_days: Days to look back
            
        Returns:
            Dict with SLA metrics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        
        query = self.db.query(CommitteeAlert).filter(
            CommitteeAlert.created_at >= cutoff_date
        )
        
        if property_id:
            query = query.filter(CommitteeAlert.property_id == property_id)
        
        alerts = query.all()
        
        total_alerts = len(alerts)
        sla_breaches = sum(
            1 for a in alerts
            if a.sla_due_at and a.sla_due_at < datetime.utcnow() and a.status != AlertStatus.RESOLVED
        )
        
        # Calculate average MTTA and MTTR
        mtta_values = [a.mtta for a in alerts if a.mtta]
        mttr_values = [a.mttr for a in alerts if a.mttr]
        
        avg_mtta = sum(mtta_values) / len(mtta_values) if mtta_values else 0
        avg_mttr = sum(mttr_values) / len(mttr_values) if mttr_values else 0
        
        return {
            'total_alerts': total_alerts,
            'sla_breaches': sla_breaches,
            'sla_compliance_rate': (1 - (sla_breaches / total_alerts)) * 100 if total_alerts > 0 else 100.0,
            'avg_mtta_minutes': avg_mtta,
            'avg_mttr_minutes': avg_mttr,
            'lookback_days': lookback_days
        }
