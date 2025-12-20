"""
Alert Escalation Service
Manages automatic escalation of alerts based on time, severity, and frequency
"""
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

from app.models.committee_alert import (
    CommitteeAlert, AlertSeverity, AlertStatus, CommitteeType
)
from sqlalchemy import and_

logger = logging.getLogger(__name__)


class AlertEscalationService:
    """
    Alert Escalation Service
    
    Manages automatic escalation:
    - Time-based (unacknowledged alerts)
    - Severity-based (critical → executive committee)
    - Frequency-based (recurring alerts)
    """
    
    # Escalation thresholds
    TIME_ESCALATION_HOURS = {
        AlertSeverity.URGENT: 1,  # 1 hour
        AlertSeverity.CRITICAL: 4,  # 4 hours
        AlertSeverity.WARNING: 24,  # 24 hours
        AlertSeverity.INFO: 72  # 72 hours
    }
    
    FREQUENCY_ESCALATION_COUNT = 3  # Escalate after 3 occurrences
    
    def __init__(self, db: Session):
        self.db = db
    
    def check_and_escalate_alerts(self) -> Dict[str, Any]:
        """
        Check all active alerts and escalate if needed
        
        Returns:
            Summary of escalation actions
        """
        # Get all active alerts
        active_alerts = self.db.query(CommitteeAlert).filter(
            CommitteeAlert.status == AlertStatus.ACTIVE
        ).all()
        
        escalated_count = 0
        escalation_details = []
        
        for alert in active_alerts:
            escalation_result = self._check_escalation(alert)
            
            if escalation_result["should_escalate"]:
                self._escalate_alert(alert, escalation_result["reason"])
                escalated_count += 1
                escalation_details.append({
                    "alert_id": alert.id,
                    "reason": escalation_result["reason"],
                    "new_level": alert.escalation_level,
                    "new_committee": alert.assigned_committee.value if alert.assigned_committee else None
                })
        
        self.db.commit()
        
        return {
            "total_checked": len(active_alerts),
            "escalated": escalated_count,
            "details": escalation_details
        }
    
    def _check_escalation(self, alert: CommitteeAlert) -> Dict[str, Any]:
        """Check if alert should be escalated"""
        reasons = []
        
        # Time-based escalation
        if self._should_escalate_by_time(alert):
            reasons.append("time_based")
        
        # Severity-based escalation
        if self._should_escalate_by_severity(alert):
            reasons.append("severity_based")
        
        # Frequency-based escalation
        if self._should_escalate_by_frequency(alert):
            reasons.append("frequency_based")
        
        return {
            "should_escalate": len(reasons) > 0,
            "reason": ", ".join(reasons) if reasons else None
        }
    
    def _should_escalate_by_time(self, alert: CommitteeAlert) -> bool:
        """Check if alert should escalate based on time"""
        if not alert.triggered_at:
            return False
        
        hours_threshold = self.TIME_ESCALATION_HOURS.get(alert.severity, 24)
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_threshold)
        
        # Check if unacknowledged and past threshold
        if alert.status == AlertStatus.ACTIVE and alert.triggered_at < cutoff_time:
            # Check if already escalated recently
            if alert.escalated_at:
                hours_since_escalation = (datetime.utcnow() - alert.escalated_at).total_seconds() / 3600
                if hours_since_escalation < hours_threshold:
                    return False  # Already escalated recently
            
            return True
        
        return False
    
    def _should_escalate_by_severity(self, alert: CommitteeAlert) -> bool:
        """Check if alert should escalate based on severity"""
        # Critical/Urgent should go to Executive Committee
        if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.URGENT]:
            if alert.assigned_committee != CommitteeType.EXECUTIVE_COMMITTEE:
                return True
        
        return False
    
    def _should_escalate_by_frequency(self, alert: CommitteeAlert) -> bool:
        """Check if alert should escalate based on frequency"""
        # Count similar alerts in last 30 days
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        similar_count = self.db.query(CommitteeAlert).filter(
            and_(
                CommitteeAlert.property_id == alert.property_id,
                CommitteeAlert.alert_type == alert.alert_type,
                CommitteeAlert.triggered_at >= cutoff_date
            )
        ).count()
        
        if similar_count >= self.FREQUENCY_ESCALATION_COUNT:
            # Check if already escalated
            if alert.escalation_level is None or alert.escalation_level < 2:
                return True
        
        return False
    
    def _escalate_alert(self, alert: CommitteeAlert, reason: str) -> None:
        """Escalate an alert"""
        # Increment escalation level
        alert.escalation_level = (alert.escalation_level or 0) + 1
        alert.escalated_at = datetime.utcnow()
        
        # Update committee assignment based on escalation level
        if alert.escalation_level >= 3:
            alert.assigned_committee = CommitteeType.EXECUTIVE_COMMITTEE
        elif alert.escalation_level >= 2:
            if alert.assigned_committee == CommitteeType.FINANCE_SUBCOMMITTEE:
                alert.assigned_committee = CommitteeType.RISK_COMMITTEE
            elif alert.assigned_committee == CommitteeType.OCCUPANCY_SUBCOMMITTEE:
                alert.assigned_committee = CommitteeType.RISK_COMMITTEE
        
        # Update metadata
        if not alert.alert_metadata:
            alert.alert_metadata = {}
        
        if "escalation_history" not in alert.alert_metadata:
            alert.alert_metadata["escalation_history"] = []
        
        alert.alert_metadata["escalation_history"].append({
            "escalated_at": datetime.utcnow().isoformat(),
            "reason": reason,
            "level": alert.escalation_level
        })
        
        logger.info(
            f"Escalated alert {alert.id} to level {alert.escalation_level} "
            f"(reason: {reason})"
        )
    
    def escalate_alert_manually(
        self,
        alert_id: int,
        reason: str,
        target_committee: Optional[CommitteeType] = None
    ) -> CommitteeAlert:
        """Manually escalate an alert"""
        alert = self.db.query(CommitteeAlert).filter(CommitteeAlert.id == alert_id).first()
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")
        
        alert.escalation_level = (alert.escalation_level or 0) + 1
        alert.escalated_at = datetime.utcnow()
        
        if target_committee:
            alert.assigned_committee = target_committee
        
        # Update metadata
        if not alert.alert_metadata:
            alert.alert_metadata = {}
        
        if "escalation_history" not in alert.alert_metadata:
            alert.alert_metadata["escalation_history"] = []
        
        alert.alert_metadata["escalation_history"].append({
            "escalated_at": datetime.utcnow().isoformat(),
            "reason": reason,
            "level": alert.escalation_level,
            "manual": True
        })
        
        self.db.commit()
        self.db.refresh(alert)
        
        logger.info(f"Manually escalated alert {alert_id} to level {alert.escalation_level}")
        
        return alert

