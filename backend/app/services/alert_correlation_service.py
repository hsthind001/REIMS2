"""
Alert Correlation Service

Groups related anomalies into incidents based on shared properties,
periods, related accounts, or root causes.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
import uuid
import logging

from app.models.committee_alert import CommitteeAlert, AlertType, AlertStatus
from app.models.anomaly_detection import AnomalyDetection

logger = logging.getLogger(__name__)


class AlertCorrelationService:
    """
    Correlates and groups related alerts into incidents.
    
    Groups by:
    - Shared properties
    - Shared periods
    - Related accounts (e.g., utility expenses)
    - Root causes
    """
    
    def __init__(self, db: Session):
        """Initialize correlation service."""
        self.db = db
    
    def correlate_alerts(
        self,
        alert_ids: List[int],
        correlation_type: str = 'auto'
    ) -> Dict[str, Any]:
        """
        Correlate alerts into incident groups.
        
        Args:
            alert_ids: List of alert IDs to correlate
            correlation_type: 'auto', 'property', 'period', 'account', 'root_cause'
            
        Returns:
            Dict with correlation results
        """
        alerts = self.db.query(CommitteeAlert).filter(
            CommitteeAlert.id.in_(alert_ids)
        ).all()
        
        if not alerts:
            return {'correlated_groups': [], 'uncorrelated': []}
        
        if correlation_type == 'auto':
            # Auto-detect correlation type
            correlation_type = self._detect_correlation_type(alerts)
        
        # Group alerts
        groups = self._group_alerts(alerts, correlation_type)
        
        # Create incident groups
        incident_groups = []
        for group in groups:
            incident_group_id = uuid.uuid4()
            
            # Create parent alert for the group
            parent_alert = self._create_parent_alert(group, incident_group_id)
            
            # Update child alerts
            for alert in group:
                alert.incident_group_id = incident_group_id
                alert.correlation_id = parent_alert.id
                self.db.commit()
            
            incident_groups.append({
                'incident_group_id': str(incident_group_id),
                'parent_alert_id': parent_alert.id,
                'child_alert_count': len(group),
                'alerts': [a.id for a in group]
            })
        
        return {
            'correlated_groups': incident_groups,
            'correlation_type': correlation_type,
            'total_groups': len(incident_groups)
        }
    
    def _detect_correlation_type(self, alerts: List[CommitteeAlert]) -> str:
        """Auto-detect best correlation type."""
        # Check if all share same property
        properties = set(a.property_id for a in alerts)
        if len(properties) == 1:
            return 'property'
        
        # Check if all share same period
        periods = set()
        for alert in alerts:
            if alert.metadata and 'period_id' in alert.metadata:
                periods.add(alert.metadata['period_id'])
        
        if len(periods) == 1:
            return 'period'
        
        # Check for related accounts
        metrics = set(a.related_metric for a in alerts if a.related_metric)
        if len(metrics) <= len(alerts) * 0.5:  # At least 50% share metrics
            return 'account'
        
        return 'root_cause'
    
    def _group_alerts(
        self,
        alerts: List[CommitteeAlert],
        correlation_type: str
    ) -> List[List[CommitteeAlert]]:
        """Group alerts based on correlation type."""
        groups = []
        processed = set()
        
        for alert in alerts:
            if alert.id in processed:
                continue
            
            group = [alert]
            processed.add(alert.id)
            
            # Find related alerts
            for other_alert in alerts:
                if other_alert.id in processed:
                    continue
                
                if self._are_related(alert, other_alert, correlation_type):
                    group.append(other_alert)
                    processed.add(other_alert.id)
            
            if len(group) > 1:
                groups.append(group)
        
        return groups
    
    def _are_related(
        self,
        alert1: CommitteeAlert,
        alert2: CommitteeAlert,
        correlation_type: str
    ) -> bool:
        """Check if two alerts are related."""
        if correlation_type == 'property':
            return alert1.property_id == alert2.property_id
        
        elif correlation_type == 'period':
            period1 = alert1.metadata.get('period_id') if alert1.metadata else None
            period2 = alert2.metadata.get('period_id') if alert2.metadata else None
            return period1 == period2
        
        elif correlation_type == 'account':
            # Related accounts (e.g., utility expenses)
            metric1 = alert1.related_metric
            metric2 = alert2.related_metric
            
            if not metric1 or not metric2:
                return False
            
            # Check if same account category
            account_categories = {
                'utility': ['electricity', 'gas', 'water', 'utility'],
                'maintenance': ['repairs', 'maintenance', 'r&m'],
                'revenue': ['rent', 'revenue', 'income']
            }
            
            for category, keywords in account_categories.items():
                if any(k in metric1.lower() for k in keywords) and any(k in metric2.lower() for k in keywords):
                    return True
            
            return metric1 == metric2
        
        elif correlation_type == 'root_cause':
            # Check metadata for root cause
            root_cause1 = alert1.metadata.get('root_cause') if alert1.metadata else None
            root_cause2 = alert2.metadata.get('root_cause') if alert2.metadata else None
            return root_cause1 == root_cause2
        
        return False
    
    def _create_parent_alert(
        self,
        child_alerts: List[CommitteeAlert],
        incident_group_id: uuid.UUID
    ) -> CommitteeAlert:
        """Create parent alert for incident group."""
        from app.models.committee_alert import AlertSeverity, CommitteeType
        
        # Determine highest severity
        severities = [a.severity for a in child_alerts]
        max_severity = max(severities, key=lambda s: s.value)
        
        # Create summary
        title = f"Incident Group: {len(child_alerts)} Related Anomalies"
        description = f"Grouped {len(child_alerts)} related anomalies:\n"
        for alert in child_alerts[:5]:  # First 5
            description += f"- {alert.title}\n"
        if len(child_alerts) > 5:
            description += f"... and {len(child_alerts) - 5} more"
        
        parent = CommitteeAlert(
            property_id=child_alerts[0].property_id,
            alert_type=AlertType.ANOMALY_DETECTED,
            severity=max_severity,
            status=AlertStatus.ACTIVE,
            title=title,
            description=description,
            assigned_committee=CommitteeType.RISK_COMMITTEE,
            incident_group_id=incident_group_id,
            metadata={
                'is_parent_alert': True,
                'child_alert_count': len(child_alerts),
                'child_alert_ids': [a.id for a in child_alerts]
            }
        )
        
        self.db.add(parent)
        self.db.commit()
        self.db.refresh(parent)
        
        return parent
