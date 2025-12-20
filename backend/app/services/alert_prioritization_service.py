"""
Alert Prioritization Service
Calculates priority scores for alerts based on multiple factors
"""
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import logging

from app.models.committee_alert import CommitteeAlert, AlertSeverity, AlertStatus
from app.models.financial_metrics import FinancialMetrics
from app.models.property import Property

logger = logging.getLogger(__name__)


class AlertPrioritizationService:
    """
    Alert Prioritization Service
    
    Calculates priority scores for alerts using multi-factor analysis:
    - Severity (from rule)
    - Breach magnitude (how far from threshold)
    - Trend direction (improving/worsening)
    - Property importance (portfolio weight)
    - Historical frequency
    - Time since last alert
    """
    
    # Weight factors for priority calculation
    SEVERITY_WEIGHT = 0.30
    BREACH_MAGNITUDE_WEIGHT = 0.25
    TREND_WEIGHT = 0.15
    PROPERTY_IMPORTANCE_WEIGHT = 0.15
    FREQUENCY_WEIGHT = 0.10
    TIME_WEIGHT = 0.05
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_priority_score(self, alert: CommitteeAlert) -> Decimal:
        """
        Calculate priority score for an alert (0-100 scale)
        
        Higher score = higher priority
        """
        try:
            # Get severity score (0-100)
            severity_score = self._get_severity_score(alert.severity)
            
            # Get breach magnitude score (0-100)
            breach_score = self._get_breach_magnitude_score(alert)
            
            # Get trend score (0-100)
            trend_score = self._get_trend_score(alert)
            
            # Get property importance score (0-100)
            property_score = self._get_property_importance_score(alert.property_id)
            
            # Get frequency score (0-100)
            frequency_score = self._get_frequency_score(alert)
            
            # Get time score (0-100)
            time_score = self._get_time_score(alert)
            
            # Weighted average
            priority = (
                severity_score * self.SEVERITY_WEIGHT +
                breach_score * self.BREACH_MAGNITUDE_WEIGHT +
                trend_score * self.TREND_WEIGHT +
                property_score * self.PROPERTY_IMPORTANCE_WEIGHT +
                frequency_score * self.FREQUENCY_WEIGHT +
                time_score * self.TIME_WEIGHT
            )
            
            return Decimal(str(round(priority, 2)))
        
        except Exception as e:
            logger.error(f"Error calculating priority for alert {alert.id}: {str(e)}", exc_info=True)
            # Return default based on severity
            return self._get_severity_score(alert.severity)
    
    def update_alert_priority(self, alert: CommitteeAlert) -> CommitteeAlert:
        """Update alert's priority score"""
        priority_score = self.calculate_priority_score(alert)
        alert.priority_score = priority_score
        self.db.commit()
        return alert
    
    def _get_severity_score(self, severity: AlertSeverity) -> float:
        """Map severity to score (0-100)"""
        severity_map = {
            AlertSeverity.URGENT: 100.0,
            AlertSeverity.CRITICAL: 90.0,
            AlertSeverity.WARNING: 60.0,
            AlertSeverity.INFO: 30.0
        }
        return severity_map.get(severity, 50.0)
    
    def _get_breach_magnitude_score(self, alert: CommitteeAlert) -> float:
        """Calculate score based on how far actual value is from threshold"""
        if not alert.threshold_value or not alert.actual_value:
            return 50.0  # Default
        
        threshold = float(alert.threshold_value)
        actual = float(alert.actual_value)
        
        # Calculate breach percentage
        if threshold == 0:
            return 50.0
        
        breach_pct = abs((actual - threshold) / threshold) * 100
        
        # Map to score (0-100)
        # 0% breach = 30, 50% breach = 100
        if breach_pct >= 50:
            return 100.0
        elif breach_pct >= 25:
            return 80.0
        elif breach_pct >= 10:
            return 60.0
        elif breach_pct >= 5:
            return 40.0
        else:
            return 30.0
    
    def _get_trend_score(self, alert: CommitteeAlert) -> float:
        """Calculate score based on trend direction"""
        if not alert.financial_period_id:
            return 50.0
        
        # Get previous period metrics
        prev_period = self.db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == alert.property_id,
            FinancialMetrics.period_id < alert.financial_period_id
        ).order_by(FinancialMetrics.period_id.desc()).first()
        
        if not prev_period:
            return 50.0
        
        # Get current period metrics
        current_metrics = self.db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == alert.property_id,
            FinancialMetrics.period_id == alert.financial_period_id
        ).first()
        
        if not current_metrics:
            return 50.0
        
        # Compare metric values (simplified - would need field_name from alert)
        # For now, return default
        return 50.0
    
    def _get_property_importance_score(self, property_id: int) -> float:
        """Calculate score based on property importance (portfolio weight, value, etc.)"""
        property_obj = self.db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            return 50.0
        
        # Use property value or other importance indicators
        # For now, return default (can be enhanced with actual property metrics)
        return 50.0
    
    def _get_frequency_score(self, alert: CommitteeAlert) -> float:
        """Calculate score based on how often this alert type occurs"""
        # Count similar alerts in last 90 days
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        similar_count = self.db.query(CommitteeAlert).filter(
            CommitteeAlert.property_id == alert.property_id,
            CommitteeAlert.alert_type == alert.alert_type,
            CommitteeAlert.triggered_at >= cutoff_date
        ).count()
        
        # More frequent = higher priority
        if similar_count >= 5:
            return 100.0
        elif similar_count >= 3:
            return 80.0
        elif similar_count >= 2:
            return 60.0
        else:
            return 40.0
    
    def _get_time_score(self, alert: CommitteeAlert) -> float:
        """Calculate score based on time since alert was triggered"""
        if not alert.triggered_at:
            return 50.0
        
        days_open = (datetime.utcnow() - alert.triggered_at).days
        
        # Older alerts = higher priority (need attention)
        if days_open >= 7:
            return 100.0
        elif days_open >= 3:
            return 80.0
        elif days_open >= 1:
            return 60.0
        else:
            return 40.0

