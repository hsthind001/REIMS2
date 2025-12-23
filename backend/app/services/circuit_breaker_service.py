"""
Circuit Breaker Service for Anomaly Alerts

Manages alert thresholds and prevents alert storms.
Notifies admins of unexpected anomaly volumes.
"""

from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import os
import logging

from app.models.committee_alert import CommitteeAlert, AlertSeverity, AlertStatus
from app.models.anomaly_detection import AnomalyDetection

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Alert storm detected, downgrading alerts
    HALF_OPEN = "half_open"  # Testing if conditions improved


class CircuitBreakerService:
    """
    Circuit breaker for anomaly alerts.
    
    Prevents alert storms by:
    - Monitoring alert volumes
    - Downgrading non-critical alerts when volume exceeds threshold
    - Escalating to admins when needed
    """
    
    def __init__(self, db: Session):
        """Initialize circuit breaker service."""
        self.db = db
        
        # Configurable thresholds
        self.alert_volume_threshold = int(os.getenv('CIRCUIT_BREAKER_ALERT_THRESHOLD', '100'))
        self.alert_volume_window_minutes = int(os.getenv('CIRCUIT_BREAKER_WINDOW_MINUTES', '60'))
        self.downgrade_severity_threshold = AlertSeverity.WARNING  # Downgrade WARNING and below
        
        # State tracking
        self.state = CircuitState.CLOSED
        self.state_changed_at = datetime.utcnow()
    
    def check_and_apply(
        self,
        alert: CommitteeAlert
    ) -> Dict[str, Any]:
        """
        Check alert volume and apply circuit breaker if needed.
        
        Args:
            alert: New alert to check
            
        Returns:
            Dict with circuit breaker action
        """
        # Check current alert volume
        volume_metrics = self._check_alert_volume()
        
        # Update circuit state
        self._update_circuit_state(volume_metrics)
        
        # Apply circuit breaker logic
        if self.state == CircuitState.OPEN:
            # Downgrade non-critical alerts
            if alert.severity.value <= self.downgrade_severity_threshold.value:
                original_severity = alert.severity
                alert.severity = AlertSeverity.INFO  # Downgrade to INFO
                
                logger.warning(
                    f"Circuit breaker OPEN: Downgraded alert {alert.id} from {original_severity} to INFO"
                )
                
                return {
                    'action': 'downgraded',
                    'original_severity': str(original_severity),
                    'new_severity': 'INFO',
                    'reason': 'Circuit breaker active - alert volume exceeded threshold'
                }
        
        # Escalate to admin if volume very high
        if volume_metrics['current_volume'] > self.alert_volume_threshold * 2:
            self._notify_admin(volume_metrics)
        
        return {
            'action': 'normal',
            'state': self.state.value,
            'volume': volume_metrics['current_volume']
        }
    
    def _check_alert_volume(self) -> Dict[str, Any]:
        """Check current alert volume in time window."""
        window_start = datetime.utcnow() - timedelta(minutes=self.alert_volume_window_minutes)
        
        current_volume = self.db.query(func.count(CommitteeAlert.id)).filter(
            and_(
                CommitteeAlert.created_at >= window_start,
                CommitteeAlert.status != AlertStatus.RESOLVED
            )
        ).scalar()
        
        # Get expected volume (average of last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        week_volume = self.db.query(func.count(CommitteeAlert.id)).filter(
            CommitteeAlert.created_at >= week_ago
        ).scalar()
        
        expected_volume = (week_volume / 7) * (self.alert_volume_window_minutes / 1440)  # Per hour
        
        return {
            'current_volume': current_volume,
            'expected_volume': expected_volume,
            'volume_ratio': current_volume / expected_volume if expected_volume > 0 else 0,
            'threshold': self.alert_volume_threshold
        }
    
    def _update_circuit_state(self, volume_metrics: Dict[str, Any]) -> None:
        """Update circuit breaker state based on volume metrics."""
        current_volume = volume_metrics['current_volume']
        volume_ratio = volume_metrics['volume_ratio']
        
        if self.state == CircuitState.CLOSED:
            if current_volume > self.alert_volume_threshold or volume_ratio > 2.0:
                self.state = CircuitState.OPEN
                self.state_changed_at = datetime.utcnow()
                logger.warning(f"Circuit breaker OPENED: Volume {current_volume} exceeds threshold {self.alert_volume_threshold}")
        
        elif self.state == CircuitState.OPEN:
            # Check if conditions improved
            if current_volume < self.alert_volume_threshold * 0.5 and volume_ratio < 1.0:
                self.state = CircuitState.HALF_OPEN
                self.state_changed_at = datetime.utcnow()
                logger.info("Circuit breaker HALF_OPEN: Conditions improving")
        
        elif self.state == CircuitState.HALF_OPEN:
            # Test period - if volume stays low, close circuit
            if current_volume < self.alert_volume_threshold * 0.7:
                self.state = CircuitState.CLOSED
                self.state_changed_at = datetime.utcnow()
                logger.info("Circuit breaker CLOSED: Normal operation resumed")
            elif current_volume > self.alert_volume_threshold:
                self.state = CircuitState.OPEN
                self.state_changed_at = datetime.utcnow()
                logger.warning("Circuit breaker RE-OPENED: Volume increased again")
    
    def _notify_admin(self, volume_metrics: Dict[str, Any]) -> None:
        """Notify admin of high alert volume."""
        logger.critical(
            f"ALERT STORM DETECTED: {volume_metrics['current_volume']} alerts in last "
            f"{self.alert_volume_window_minutes} minutes. Expected: {volume_metrics['expected_volume']:.1f}. "
            f"Admin notification required."
        )
        
        # In production, would send email/notification to admin
