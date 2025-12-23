"""
Alert Workflow Service

Manages alert snoozing, suppression, and learning from dismissals.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.alert_suppression import AlertSuppression, AlertSnooze, AlertSuppressionRule
from app.models.financial_period import FinancialPeriod

logger = logging.getLogger(__name__)


class AlertWorkflowService:
    """Service for alert workflow management"""
    
    def __init__(self, db: Session):
        """
        Initialize alert workflow service
        
        Args:
            db: Database session
        """
        self.db = db
    
    def snooze_alert(
        self,
        alert_id: int,
        until_period_id: Optional[int] = None,
        until_date: Optional[datetime] = None,
        reason: Optional[str] = None,
        snoozed_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Snooze an alert until next period or date
        
        Args:
            alert_id: Alert ID to snooze
            until_period_id: Optional period ID to snooze until
            until_date: Optional date to snooze until
            reason: Optional reason for snoozing
            snoozed_by: User ID who snoozed
            
        Returns:
            Dict with snooze details
        """
        # Check if already snoozed
        existing = self.db.query(AlertSnooze).filter(
            AlertSnooze.alert_id == alert_id
        ).first()
        
        if existing:
            # Update existing snooze
            existing.until_period_id = until_period_id
            existing.until_date = until_date
            existing.snooze_reason = reason
        else:
            # Create new snooze
            snooze = AlertSnooze(
                alert_id=alert_id,
                until_period_id=until_period_id,
                until_date=until_date,
                snooze_reason=reason,
                snoozed_by=snoozed_by
            )
            self.db.add(snooze)
            existing = snooze
        
        self.db.commit()
        self.db.refresh(existing)
        
        logger.info(f"Snoozed alert {alert_id} until period {until_period_id} or date {until_date}")
        
        return {
            'success': True,
            'alert_id': alert_id,
            'until_period_id': until_period_id,
            'until_date': until_date.isoformat() if until_date else None,
            'reason': reason
        }
    
    def suppress_alert(
        self,
        alert_id: Optional[int] = None,
        alert_type: Optional[str] = None,
        rule_id: Optional[int] = None,
        reason: str = "Suppressed by user",
        expires_at: Optional[datetime] = None,
        expires_after_periods: Optional[int] = None,
        property_id: Optional[int] = None,
        account_code: Optional[str] = None,
        suppressed_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Suppress an alert with optional expiry
        
        Args:
            alert_id: Specific alert ID to suppress
            alert_type: Alert type pattern to suppress
            rule_id: Suppression rule ID
            reason: Suppression reason
            expires_at: When suppression expires
            expires_after_periods: Expire after N periods
            property_id: Property scope
            account_code: Account scope
            suppressed_by: User ID who suppressed
            
        Returns:
            Dict with suppression details
        """
        suppression = AlertSuppression(
            alert_id=alert_id,
            alert_type=alert_type,
            rule_id=rule_id,
            suppression_reason=reason,
            expires_at=expires_at,
            expires_after_periods=expires_after_periods,
            property_id=property_id,
            account_code=account_code,
            suppressed_by=suppressed_by
        )
        
        self.db.add(suppression)
        self.db.commit()
        self.db.refresh(suppression)
        
        logger.info(f"Suppressed alert {alert_id or alert_type} (rule: {rule_id})")
        
        return {
            'success': True,
            'suppression_id': suppression.id,
            'alert_id': alert_id,
            'alert_type': alert_type,
            'expires_at': expires_at.isoformat() if expires_at else None
        }
    
    def is_alert_suppressed(
        self,
        alert_id: Optional[int] = None,
        alert_type: Optional[str] = None
    ) -> bool:
        """
        Check if an alert is currently suppressed
        
        Args:
            alert_id: Alert ID
            alert_type: Alert type
            
        Returns:
            True if suppressed, False otherwise
        """
        now = datetime.utcnow()
        
        query = self.db.query(AlertSuppression).filter(
            or_(
                AlertSuppression.alert_id == alert_id,
                (AlertSuppression.alert_type == alert_type if alert_type else False)
            ),
            or_(
                AlertSuppression.expires_at.is_(None),
                AlertSuppression.expires_at > now
            )
        )
        
        return query.first() is not None
    
    def is_alert_snoozed(
        self,
        alert_id: int
    ) -> bool:
        """
        Check if an alert is currently snoozed
        
        Args:
            alert_id: Alert ID
            
        Returns:
            True if snoozed, False otherwise
        """
        now = datetime.utcnow()
        
        snooze = self.db.query(AlertSnooze).filter(
            AlertSnooze.alert_id == alert_id,
            or_(
                AlertSnooze.until_date.is_(None),
                AlertSnooze.until_date > now
            )
        ).first()
        
        if snooze and snooze.until_period_id:
            # Check if current period is after snooze period
            current_period = self.db.query(FinancialPeriod).filter(
                FinancialPeriod.id == snooze.until_period_id
            ).first()
            if current_period:
                # TODO: Check if we're past this period
                pass
        
        return snooze is not None
    
    def learn_from_dismissals(
        self,
        property_id: Optional[int] = None,
        alert_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Learn from repeated dismissals and suggest threshold/rule tuning
        
        Args:
            property_id: Optional property ID
            alert_type: Optional alert type
            
        Returns:
            Dict with learning suggestions
        """
        # Get dismissed alerts (status = dismissed or resolved with "false_positive")
        # This would need to query the actual alert table
        # For now, return a placeholder structure
        
        suggestions = []
        
        # Example: If same alert type dismissed 5+ times, suggest threshold adjustment
        # This would require integration with the actual alert system
        
        return {
            'suggestions': suggestions,
            'message': 'Learning from dismissals requires integration with alert system'
        }
    
    def get_suppression_rules(
        self,
        property_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get active suppression rules
        
        Args:
            property_id: Optional property ID filter
            
        Returns:
            List of suppression rules
        """
        query = self.db.query(AlertSuppressionRule).filter(
            AlertSuppressionRule.is_active == True
        )
        
        if property_id:
            query = query.filter(
                or_(
                    AlertSuppressionRule.property_id == property_id,
                    AlertSuppressionRule.property_id.is_(None)
                )
            )
        
        rules = query.all()
        
        return [
            {
                'id': r.id,
                'rule_name': r.rule_name,
                'alert_type_pattern': r.alert_type_pattern,
                'condition_json': r.condition_json,
                'expires_after_periods': r.expires_after_periods,
                'expires_after_days': r.expires_after_days,
                'property_id': r.property_id,
                'account_code': r.account_code
            }
            for r in rules
        ]

