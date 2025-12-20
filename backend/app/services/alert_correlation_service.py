"""
Alert Correlation Service
Groups related alerts and identifies patterns
"""
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import logging

from app.models.committee_alert import CommitteeAlert, AlertStatus
from sqlalchemy import and_, or_
from typing import Any

logger = logging.getLogger(__name__)


class AlertCorrelationService:
    """
    Alert Correlation Service
    
    Groups related alerts and identifies patterns:
    - Same property, period, metric family
    - Alert patterns
    - Parent-child relationships
    - Root cause analysis
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def correlate_alerts(
        self,
        property_id: int,
        period_id: Optional[int] = None,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Correlate alerts for a property/period
        
        Args:
            property_id: Property ID
            period_id: Optional period ID (if None, uses all periods)
            time_window_hours: Time window for correlation
        
        Returns:
            {
                "correlation_groups": List of grouped alerts,
                "patterns": List of identified patterns,
                "root_causes": List of potential root causes
            }
        """
        # Get alerts to correlate
        query = self.db.query(CommitteeAlert).filter(
            CommitteeAlert.property_id == property_id,
            CommitteeAlert.status == AlertStatus.ACTIVE
        )
        
        if period_id:
            query = query.filter(CommitteeAlert.financial_period_id == period_id)
        
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        query = query.filter(CommitteeAlert.triggered_at >= cutoff_time)
        
        alerts = query.all()
        
        if not alerts:
            return {
                "correlation_groups": [],
                "patterns": [],
                "root_causes": []
            }
        
        # Group alerts
        groups = self._group_alerts(alerts)
        
        # Identify patterns
        patterns = self._identify_patterns(alerts)
        
        # Root cause analysis
        root_causes = self._analyze_root_causes(alerts, groups)
        
        # Update correlation_group_id for alerts
        for group_id, group_alerts in enumerate(groups, start=1):
            for alert in group_alerts:
                alert.correlation_group_id = group_id
        
        self.db.commit()
        
        return {
            "correlation_groups": [
                {
                    "group_id": idx,
                    "alerts": [self._alert_to_dict(a) for a in group],
                    "common_factors": self._get_common_factors(group)
                }
                for idx, group in enumerate(groups, start=1)
            ],
            "patterns": patterns,
            "root_causes": root_causes
        }
    
    def _group_alerts(self, alerts: List[CommitteeAlert]) -> List[List[CommitteeAlert]]:
        """Group related alerts"""
        groups = []
        processed = set()
        
        for alert in alerts:
            if alert.id in processed:
                continue
            
            # Find related alerts
            related = [alert]
            processed.add(alert.id)
            
            for other in alerts:
                if other.id in processed:
                    continue
                
                if self._are_related(alert, other):
                    related.append(other)
                    processed.add(other.id)
            
            if len(related) > 1:
                groups.append(related)
            else:
                # Single alert group
                groups.append(related)
        
        return groups
    
    def _are_related(self, alert1: CommitteeAlert, alert2: CommitteeAlert) -> bool:
        """Check if two alerts are related"""
        # Same property and period
        if (alert1.property_id == alert2.property_id and
            alert1.financial_period_id == alert2.financial_period_id):
            return True
        
        # Same metric family
        if self._same_metric_family(alert1.alert_type, alert2.alert_type):
            return True
        
        # Triggered within 1 hour
        if abs((alert1.triggered_at - alert2.triggered_at).total_seconds()) < 3600:
            if alert1.property_id == alert2.property_id:
                return True
        
        return False
    
    def _same_metric_family(self, type1, type2) -> bool:
        """Check if alert types are in the same metric family"""
        families = {
            "financial": [
                "DSCR_BREACH", "DEBT_YIELD_BREACH", "INTEREST_COVERAGE_BREACH",
                "CASH_FLOW_NEGATIVE", "REVENUE_DECLINE", "EXPENSE_SPIKE"
            ],
            "occupancy": [
                "OCCUPANCY_WARNING", "OCCUPANCY_CRITICAL",
                "BREAK_EVEN_OCCUPANCY_BREACH", "RENT_COLLECTION_RATE"
            ],
            "risk": [
                "LTV_BREACH", "LIQUIDITY_WARNING", "DEBT_TO_EQUITY_BREACH"
            ]
        }
        
        for family, types in families.items():
            if type1.value in types and type2.value in types:
                return True
        
        return False
    
    def _identify_patterns(self, alerts: List[CommitteeAlert]) -> List[Dict]:
        """Identify alert patterns"""
        patterns = []
        
        # Pattern: Multiple financial alerts
        financial_alerts = [a for a in alerts if a.alert_type.value in [
            "DSCR_BREACH", "CASH_FLOW_NEGATIVE", "REVENUE_DECLINE"
        ]]
        if len(financial_alerts) >= 2:
            patterns.append({
                "type": "multiple_financial_issues",
                "description": f"{len(financial_alerts)} financial alerts detected",
                "severity": "high",
                "alerts": [a.id for a in financial_alerts]
            })
        
        # Pattern: Escalating severity
        severity_order = ["INFO", "WARNING", "CRITICAL", "URGENT"]
        for i in range(len(alerts) - 1):
            if (severity_order.index(alerts[i].severity.value) <
                severity_order.index(alerts[i+1].severity.value)):
                patterns.append({
                    "type": "escalating_severity",
                    "description": "Alert severity is escalating",
                    "severity": "medium",
                    "alerts": [alerts[i].id, alerts[i+1].id]
                })
        
        return patterns
    
    def _analyze_root_causes(self, alerts: List[CommitteeAlert], groups: List[List[CommitteeAlert]]) -> List[Dict]:
        """Analyze potential root causes"""
        root_causes = []
        
        # Root cause: Revenue decline causing multiple issues
        revenue_alerts = [a for a in alerts if a.alert_type.value == "REVENUE_DECLINE"]
        if revenue_alerts:
            related = [a for a in alerts if a.property_id == revenue_alerts[0].property_id]
            if len(related) > 1:
                root_causes.append({
                    "type": "revenue_decline",
                    "description": "Revenue decline may be causing multiple financial issues",
                    "confidence": "high",
                    "related_alerts": [a.id for a in related]
                })
        
        # Root cause: Occupancy issues
        occupancy_alerts = [a for a in alerts if "OCCUPANCY" in a.alert_type.value]
        if occupancy_alerts:
            root_causes.append({
                "type": "occupancy_issues",
                "description": "Occupancy problems detected",
                "confidence": "medium",
                "related_alerts": [a.id for a in occupancy_alerts]
            })
        
        return root_causes
    
    def _get_common_factors(self, group: List[CommitteeAlert]) -> Dict:
        """Get common factors for a group of alerts"""
        if not group:
            return {}
        
        return {
            "property_id": group[0].property_id,
            "period_id": group[0].financial_period_id,
            "alert_count": len(group),
            "severity_range": [
                min(a.severity.value for a in group),
                max(a.severity.value for a in group)
            ],
            "time_range": [
                min(a.triggered_at for a in group).isoformat(),
                max(a.triggered_at for a in group).isoformat()
            ]
        }
    
    def _alert_to_dict(self, alert: CommitteeAlert) -> Dict:
        """Convert alert to dict for response"""
        return {
            "id": alert.id,
            "alert_type": alert.alert_type.value if alert.alert_type else None,
            "severity": alert.severity.value if alert.severity else None,
            "title": alert.title,
            "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None
        }

