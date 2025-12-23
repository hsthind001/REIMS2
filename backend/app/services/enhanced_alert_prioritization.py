"""
Enhanced Alert Prioritization Service

Calculates business impact score and updates priority_score in committee_alerts.
Combines: severity, dollar impact, covenant proximity, portfolio importance.
"""

from typing import Dict, Optional, Any
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging

from app.models.committee_alert import CommitteeAlert, AlertSeverity
from app.models.anomaly_detection import AnomalyDetection
from app.models.financial_metrics import FinancialMetrics
from app.models.property import Property

logger = logging.getLogger(__name__)


class EnhancedAlertPrioritizationService:
    """
    Calculates business impact score for alerts.
    
    Components:
    - Severity (URGENT=100, CRITICAL=75, WARNING=50, INFO=25)
    - Dollar Impact (normalized 0-100)
    - Covenant Proximity (DSCR distance to threshold)
    - Portfolio Importance (NOI and loan balance weighted)
    """
    
    def __init__(self, db: Session):
        """Initialize prioritization service."""
        self.db = db
    
    def calculate_business_impact_score(
        self,
        alert_id: int
    ) -> Dict[str, Any]:
        """
        Calculate business impact score for an alert.
        
        Args:
            alert_id: CommitteeAlert ID
            
        Returns:
            Dict with business_impact_score and component breakdown
        """
        alert = self.db.query(CommitteeAlert).filter(
            CommitteeAlert.id == alert_id
        ).first()
        
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")
        
        # 1. Severity component (0-100)
        severity_score = self._calculate_severity_score(alert.severity)
        
        # 2. Dollar impact component (0-100)
        dollar_impact_score = self._calculate_dollar_impact_score(alert)
        
        # 3. Covenant proximity component (0-100)
        covenant_score = self._calculate_covenant_proximity_score(alert)
        
        # 4. Portfolio importance component (0-100)
        portfolio_score = self._calculate_portfolio_importance_score(alert)
        
        # Weighted combination
        weights = {
            'severity': 0.30,
            'dollar_impact': 0.35,
            'covenant': 0.25,
            'portfolio': 0.10
        }
        
        business_impact_score = (
            severity_score * weights['severity'] +
            dollar_impact_score * weights['dollar_impact'] +
            covenant_score * weights['covenant'] +
            portfolio_score * weights['portfolio']
        )
        
        # Update alert
        alert.business_impact_score = Decimal(str(business_impact_score))
        alert.priority_score = Decimal(str(business_impact_score))  # Same as business impact
        self.db.commit()
        
        return {
            'business_impact_score': business_impact_score,
            'priority_score': business_impact_score,
            'components': {
                'severity': severity_score,
                'dollar_impact': dollar_impact_score,
                'covenant': covenant_score,
                'portfolio': portfolio_score
            }
        }
    
    def _calculate_severity_score(self, severity: AlertSeverity) -> float:
        """Calculate severity component (0-100)."""
        severity_map = {
            AlertSeverity.URGENT: 100.0,
            AlertSeverity.CRITICAL: 75.0,
            AlertSeverity.WARNING: 50.0,
            AlertSeverity.INFO: 25.0
        }
        return severity_map.get(severity, 25.0)
    
    def _calculate_dollar_impact_score(self, alert: CommitteeAlert) -> float:
        """Calculate dollar impact component (0-100)."""
        # Get associated anomaly
        anomaly = None
        if alert.metadata and 'anomaly_id' in alert.metadata:
            anomaly = self.db.query(AnomalyDetection).filter(
                AnomalyDetection.id == alert.metadata['anomaly_id']
            ).first()
        
        if not anomaly or not anomaly.impact_amount:
            return 0.0
        
        # Normalize impact amount to 0-100 scale
        # $10K = 100 points, $1K = 10 points
        impact_amount = abs(float(anomaly.impact_amount))
        dollar_score = min(100.0, impact_amount / 100.0)  # $10K = 100 points
        
        return dollar_score
    
    def _calculate_covenant_proximity_score(self, alert: CommitteeAlert) -> float:
        """Calculate covenant proximity component (0-100)."""
        # Get property metrics
        metrics = self.db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == alert.property_id
        ).order_by(FinancialMetrics.period_id.desc()).first()
        
        if not metrics or not metrics.net_operating_income:
            return 0.0
        
        # Calculate DSCR
        noi = float(metrics.net_operating_income)
        total_debt = float(metrics.total_debt) if metrics.total_debt else 0.0
        
        if total_debt == 0:
            return 0.0
        
        # Estimate annual debt service (5% interest rate)
        annual_debt_service = (total_debt * 0.05)
        dscr = noi / annual_debt_service if annual_debt_service > 0 else 0.0
        
        # DSCR threshold
        dscr_threshold = 1.25
        
        # Calculate proximity score
        distance_to_threshold = dscr - dscr_threshold
        
        if distance_to_threshold < 0:
            # Below threshold - critical
            return 100.0
        elif distance_to_threshold < 0.1:
            # Very close - high risk
            return 90.0
        elif distance_to_threshold < 0.25:
            # Close - medium-high risk
            return 70.0
        elif distance_to_threshold < 0.5:
            # Moderate distance - medium risk
            return 40.0
        else:
            # Safe distance - low risk
            return 10.0
    
    def _calculate_portfolio_importance_score(self, alert: CommitteeAlert) -> float:
        """Calculate portfolio importance component (0-100)."""
        property = self.db.query(Property).filter(
            Property.id == alert.property_id
        ).first()
        
        if not property:
            return 0.0
        
        # Get metrics
        metrics = self.db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == alert.property_id
        ).order_by(FinancialMetrics.period_id.desc()).first()
        
        if not metrics:
            return 0.0
        
        # Normalize NOI and loan balance
        # Assume max NOI in portfolio is $10M, max loan is $50M
        max_noi = 10_000_000
        max_loan = 50_000_000
        
        noi = float(metrics.net_operating_income) if metrics.net_operating_income else 0.0
        loan_balance = float(metrics.total_debt) if metrics.total_debt else 0.0
        
        noi_score = min(100.0, (noi / max_noi) * 100.0) if max_noi > 0 else 0.0
        loan_score = min(100.0, (loan_balance / max_loan) * 100.0) if max_loan > 0 else 0.0
        
        # Weighted average
        portfolio_score = (noi_score * 0.6 + loan_score * 0.4)
        
        return portfolio_score
