"""
Alert Trigger Service
Automatically triggers alerts based on rule evaluation after document processing
"""
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from app.models.financial_metrics import FinancialMetrics
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.services.alert_rules_service import AlertRulesService
from app.services.alert_creation_service import AlertCreationService

logger = logging.getLogger(__name__)


class AlertTriggerService:
    """
    Alert Trigger Service
    
    Evaluates alert rules and triggers alerts when conditions are met.
    Called automatically after document processing and metrics calculation.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.rules_service = AlertRulesService(db)
        self.creation_service = AlertCreationService(db)
    
    def evaluate_and_trigger_alerts(
        self,
        property_id: int,
        period_id: int,
        metrics: Optional[FinancialMetrics] = None,
        ignore_cooldown: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Evaluate all active rules for a property/period and trigger alerts
        
        Args:
            property_id: Property ID
            period_id: Financial period ID
            metrics: FinancialMetrics object (if None, will fetch)
        
        Returns:
            List of created alerts
        """
        try:
            # Get metrics if not provided
            if metrics is None:
                metrics = self.db.query(FinancialMetrics).filter(
                    FinancialMetrics.property_id == property_id,
                    FinancialMetrics.period_id == period_id
                ).first()
            
            if not metrics:
                logger.warning(f"No metrics found for property {property_id}, period {period_id}")
                return []
            
            # Evaluate all active rules
            evaluation_results = self.rules_service.evaluate_all_rules(
                property_id=property_id,
                period_id=period_id,
                metrics=metrics,
                ignore_cooldown=ignore_cooldown
            )
            
            if not evaluation_results:
                logger.debug(f"No rules triggered for property {property_id}, period {period_id}")
                return []
            
            # Create alerts for triggered rules
            created_alerts = []
            for result in evaluation_results:
                try:
                    alert = self.creation_service.create_alert_from_rule_result(
                        rule=result["rule"],
                        property_id=property_id,
                        period_id=period_id,
                        evaluation_result=result,
                        metrics=metrics
                    )
                    
                    if alert:
                        created_alerts.append({
                            "alert_id": alert.id,
                            "alert_type": alert.alert_type.value if alert.alert_type else None,
                            "severity": alert.severity.value if alert.severity else None,
                            "title": alert.title
                        })
                
                except Exception as e:
                    logger.error(
                        f"Error creating alert from rule {result['rule'].id}: {str(e)}",
                        exc_info=True
                    )
                    continue
            
            logger.info(
                f"Triggered {len(created_alerts)} alerts for property {property_id}, period {period_id}"
            )
            
            return created_alerts
        
        except Exception as e:
            logger.error(
                f"Error evaluating alerts for property {property_id}, period {period_id}: {str(e)}",
                exc_info=True
            )
            # Don't fail document processing if alert generation fails
            return []
    
    def evaluate_property_alerts(
        self,
        property_id: int,
        period_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Evaluate alerts for a property (all periods or specific period)
        
        Args:
            property_id: Property ID
            period_id: If provided, only evaluate for this period
        
        Returns:
            Summary of evaluation results
        """
        if period_id:
            periods = [self.db.query(FinancialPeriod).filter(FinancialPeriod.id == period_id).first()]
        else:
            # Get all periods for property
            periods = self.db.query(FinancialPeriod).filter(
                FinancialPeriod.property_id == property_id
            ).order_by(FinancialPeriod.period_end_date.desc()).all()
        
        total_alerts = 0
        alerts_by_period = {}
        
        for period in periods:
            if not period:
                continue
            
            alerts = self.evaluate_and_trigger_alerts(
                property_id=property_id,
                period_id=period.id
            )
            
            alerts_by_period[period.id] = {
                "period_id": period.id,
                "period_name": period.period_name,
                "alert_count": len(alerts),
                "alerts": alerts
            }
            
            total_alerts += len(alerts)
        
        return {
            "property_id": property_id,
            "total_alerts_triggered": total_alerts,
            "periods_evaluated": len(periods),
            "alerts_by_period": alerts_by_period
        }
