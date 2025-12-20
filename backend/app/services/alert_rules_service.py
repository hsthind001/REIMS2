"""
Alert Rules Service
Evaluates alert rules against financial metrics and determines if alerts should be triggered
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
import logging
import json

from app.models.alert_rule import AlertRule, RuleType, RuleCondition
from app.models.financial_metrics import FinancialMetrics
from app.models.property import Property
from app.models.financial_period import FinancialPeriod

logger = logging.getLogger(__name__)


class AlertRulesService:
    """
    Alert Rules Evaluation Service
    
    Evaluates alert rules against financial metrics and determines
    if alerts should be triggered based on rule conditions.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._rule_cache = {}  # Cache compiled rules for performance
    
    def get_active_rules(
        self,
        property_id: Optional[int] = None,
        rule_type: Optional[str] = None
    ) -> List[AlertRule]:
        """
        Get active alert rules
        
        Args:
            property_id: If provided, returns property-specific rules + global rules
            rule_type: Filter by rule type
        
        Returns:
            List of active AlertRule objects
        """
        query = self.db.query(AlertRule).filter(AlertRule.is_active == True)
        
        if property_id:
            # Get property-specific rules + global rules
            query = query.filter(
                or_(
                    AlertRule.property_id == property_id,
                    AlertRule.property_specific == False
                )
            )
        else:
            # Only global rules
            query = query.filter(AlertRule.property_specific == False)
        
        if rule_type:
            query = query.filter(AlertRule.rule_type == rule_type)
        
        return query.all()
    
    def evaluate_rule(
        self,
        rule: AlertRule,
        property_id: int,
        period_id: int,
        metrics: Optional[FinancialMetrics] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a single rule against current metrics
        
        Args:
            rule: AlertRule to evaluate
            property_id: Property ID
            period_id: Financial period ID
            metrics: FinancialMetrics object (if None, will fetch)
        
        Returns:
            {
                "triggered": bool,
                "severity": str,
                "actual_value": float,
                "threshold_value": float,
                "breach_magnitude": float,
                "message": str,
                "metadata": dict
            }
        """
        try:
            # Check cooldown
            if rule.is_in_cooldown():
                return {
                    "triggered": False,
                    "reason": "cooldown",
                    "cooldown_until": rule.last_triggered_at + timedelta(minutes=rule.cooldown_period) if rule.last_triggered_at else None
                }
            
            # Get metrics if not provided
            if metrics is None:
                metrics = self.db.query(FinancialMetrics).filter(
                    and_(
                        FinancialMetrics.property_id == property_id,
                        FinancialMetrics.period_id == period_id
                    )
                ).first()
            
            if not metrics:
                return {
                    "triggered": False,
                    "reason": "no_metrics",
                    "message": "No financial metrics found for property/period"
                }
            
            # Get the field value based on rule.field_name
            field_value = self._get_field_value(rule.field_name, metrics)
            
            if field_value is None:
                return {
                    "triggered": False,
                    "reason": "field_not_found",
                    "message": f"Field '{rule.field_name}' not found in metrics"
                }
            
            # Evaluate condition
            threshold = float(rule.threshold_value) if rule.threshold_value else None
            triggered, breach_magnitude = self._evaluate_condition(
                rule.condition,
                field_value,
                threshold,
                metrics,
                property_id,
                period_id
            )
            
            if not triggered:
                return {
                    "triggered": False,
                    "reason": "condition_not_met",
                    "actual_value": float(field_value),
                    "threshold_value": threshold
                }
            
            # Determine severity (use severity_mapping if available)
            severity = self._determine_severity(rule, breach_magnitude, field_value, threshold)
            
            # Generate message
            message = self._generate_alert_message(rule, field_value, threshold, breach_magnitude)
            
            # Update rule execution tracking
            rule.execution_count = (rule.execution_count or 0) + 1
            rule.last_triggered_at = datetime.utcnow()
            self.db.commit()
            
            return {
                "triggered": True,
                "severity": severity,
                "actual_value": float(field_value),
                "threshold_value": threshold,
                "breach_magnitude": breach_magnitude,
                "message": message,
                "metadata": {
                    "rule_id": rule.id,
                    "rule_name": rule.rule_name,
                    "field_name": rule.field_name,
                    "condition": rule.condition.value if rule.condition else None,
                    "breach_percentage": abs(breach_magnitude) * 100 if breach_magnitude else 0
                }
            }
        
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.id}: {str(e)}", exc_info=True)
            return {
                "triggered": False,
                "reason": "error",
                "error": str(e)
            }
    
    def evaluate_all_rules(
        self,
        property_id: int,
        period_id: int,
        metrics: Optional[FinancialMetrics] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate all active rules for a property/period
        
        Returns:
            List of evaluation results (only triggered rules)
        """
        rules = self.get_active_rules(property_id=property_id)
        results = []
        
        for rule in rules:
            result = self.evaluate_rule(rule, property_id, period_id, metrics)
            if result.get("triggered"):
                results.append({
                    "rule": rule,
                    **result
                })
        
        return results
    
    def _get_field_value(self, field_name: str, metrics: FinancialMetrics) -> Optional[Decimal]:
        """
        Get field value from FinancialMetrics object
        
        Supports:
        - Direct attribute access (e.g., "dscr", "occupancy_rate")
        - Account codes (e.g., "1999-0000" for Total Assets)
        - Calculated fields
        """
        # Try direct attribute access first
        if hasattr(metrics, field_name):
            value = getattr(metrics, field_name)
            if value is not None:
                return Decimal(str(value))
        
        # Try common metric aliases
        metric_aliases = {
            "dscr": "dscr",
            "debt_service_coverage_ratio": "dscr",
            "ltv": "ltv",
            "loan_to_value": "ltv",
            "occupancy": "occupancy_rate",
            "occupancy_rate": "occupancy_rate",
            "noi": "net_operating_income",
            "net_operating_income": "net_operating_income",
            "debt_yield": "debt_yield",
            "interest_coverage": "interest_coverage_ratio",
            "current_ratio": "current_ratio",
            "debt_to_equity": "debt_to_equity_ratio",
        }
        
        if field_name.lower() in metric_aliases:
            attr_name = metric_aliases[field_name.lower()]
            if hasattr(metrics, attr_name):
                value = getattr(metrics, attr_name)
                if value is not None:
                    return Decimal(str(value))
        
        # For account codes, we'd need to query the financial data tables
        # This is a simplified version - can be enhanced
        return None
    
    def _evaluate_condition(
        self,
        condition: RuleCondition,
        field_value: Decimal,
        threshold: Optional[float],
        metrics: FinancialMetrics,
        property_id: int,
        period_id: int
    ) -> Tuple[bool, float]:
        """
        Evaluate rule condition
        
        Returns:
            (triggered: bool, breach_magnitude: float)
        """
        if threshold is None:
            return False, 0.0
        
        field_float = float(field_value)
        breach_magnitude = 0.0
        
        if condition == "less_than":
            triggered = field_float < threshold
            if triggered:
                breach_magnitude = (field_float - threshold) / threshold if threshold != 0 else 0
        
        elif condition == "greater_than":
            triggered = field_float > threshold
            if triggered:
                breach_magnitude = (field_float - threshold) / threshold if threshold != 0 else 0
        
        elif condition == "equals":
            triggered = abs(field_float - threshold) < 0.01  # Small tolerance
            breach_magnitude = 0
        
        elif condition == "not_equals":
            triggered = abs(field_float - threshold) >= 0.01
            breach_magnitude = 0
        
        elif condition == "percentage_change":
            # Compare with previous period - would need field_name from rule context
            # For now, simplified implementation
            triggered = False
            breach_magnitude = 0.0
        
        elif condition == "z_score":
            # Calculate z-score (requires historical data)
            # Need field_name from rule - simplified for now
            z_score = 0.0  # Would calculate with field_name
            triggered = False
            breach_magnitude = 0.0
        
        else:
            triggered = False
        
        return triggered, breach_magnitude
    
    def _determine_severity(
        self,
        rule: AlertRule,
        breach_magnitude: float,
        actual_value: Decimal,
        threshold: Optional[float]
    ) -> str:
        """
        Determine alert severity based on rule and breach magnitude
        
        Uses severity_mapping if available, otherwise uses rule.severity
        """
        if rule.severity_mapping:
            # Dynamic severity based on breach magnitude
            try:
                mapping = rule.severity_mapping
                abs_breach = abs(breach_magnitude)
                
                # Check severity thresholds in order (most severe first)
                if mapping.get("critical_threshold") and abs_breach >= mapping["critical_threshold"]:
                    return "critical"
                elif mapping.get("high_threshold") and abs_breach >= mapping["high_threshold"]:
                    return "high"
                elif mapping.get("warning_threshold") and abs_breach >= mapping["warning_threshold"]:
                    return "warning"
                else:
                    return "info"
            except Exception:
                pass
        
        # Fallback to rule severity
        return rule.severity or "warning"
    
    def _generate_alert_message(
        self,
        rule: AlertRule,
        actual_value: Decimal,
        threshold: Optional[float],
        breach_magnitude: float
    ) -> str:
        """Generate human-readable alert message"""
        field_display = rule.field_name.replace("_", " ").title()
        actual_str = f"{float(actual_value):,.2f}"
        threshold_str = f"{threshold:,.2f}" if threshold else "N/A"
        breach_pct = abs(breach_magnitude) * 100
        
        if rule.condition == "less_than":
            return f"{field_display} is {actual_str}, which is below the threshold of {threshold_str} ({breach_pct:.1f}% below threshold)"
        elif rule.condition == "greater_than":
            return f"{field_display} is {actual_str}, which exceeds the threshold of {threshold_str} ({breach_pct:.1f}% above threshold)"
        else:
            return f"{field_display} is {actual_str}, which violates the rule threshold of {threshold_str}"
    
    def _get_previous_period_metrics(
        self,
        property_id: int,
        period_id: int
    ) -> Optional[FinancialMetrics]:
        """Get metrics for previous period"""
        current_period = self.db.query(FinancialPeriod).filter(
            FinancialPeriod.id == period_id
        ).first()
        
        if not current_period:
            return None
        
        # Find previous period (same property, previous month)
        prev_period = self.db.query(FinancialPeriod).filter(
            and_(
                FinancialPeriod.property_id == property_id,
                FinancialPeriod.period_end_date < current_period.period_end_date
            )
        ).order_by(FinancialPeriod.period_end_date.desc()).first()
        
        if not prev_period:
            return None
        
        return self.db.query(FinancialMetrics).filter(
            and_(
                FinancialMetrics.property_id == property_id,
                FinancialMetrics.period_id == prev_period.id
            )
        ).first()
    
    def _calculate_z_score(
        self,
        property_id: int,
        value: Decimal,
        current_metrics: FinancialMetrics,
        field_name: str
    ) -> float:
        """
        Calculate z-score for a value based on historical data
        
        Z-score = (value - mean) / std_dev
        """
        # Get historical metrics (last 12 periods)
        periods = self.db.query(FinancialPeriod).filter(
            FinancialPeriod.property_id == property_id
        ).order_by(FinancialPeriod.period_end_date.desc()).limit(12).all()
        
        if len(periods) < 3:  # Need at least 3 data points
            return 0.0
        
        period_ids = [p.id for p in periods]
        historical_metrics = self.db.query(FinancialMetrics).filter(
            and_(
                FinancialMetrics.property_id == property_id,
                FinancialMetrics.period_id.in_(period_ids)
            )
        ).all()
        
        # Extract values for the field
        values = []
        for m in historical_metrics:
            field_val = self._get_field_value(field_name, m)
            if field_val is not None:
                values.append(float(field_val))
        
        if len(values) < 3:
            return 0.0
        
        import statistics
        mean = statistics.mean(values)
        std_dev = statistics.stdev(values) if len(values) > 1 else 1.0
        
        if std_dev == 0:
            return 0.0
        
        z_score = (float(value) - mean) / std_dev
        return z_score

