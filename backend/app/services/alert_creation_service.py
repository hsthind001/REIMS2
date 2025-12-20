"""
Alert Creation Service
Creates CommitteeAlert records from rule evaluation results
"""
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from app.models.committee_alert import (
    CommitteeAlert, AlertType, AlertSeverity, AlertStatus, CommitteeType
)
from app.models.alert_rule import AlertRule
from app.models.financial_metrics import FinancialMetrics
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.services.alert_notification_service import AlertNotificationService
from app.services.workflow_lock_service import WorkflowLockService
from app.models.workflow_lock import LockReason, LockScope

logger = logging.getLogger(__name__)


class AlertCreationService:
    """
    Alert Creation Service
    
    Creates standardized CommitteeAlert records from rule evaluation results.
    Handles alert deduplication, metadata enrichment, and committee assignment.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_alert_from_rule_result(
        self,
        rule: AlertRule,
        property_id: int,
        period_id: int,
        evaluation_result: Dict[str, Any],
        metrics: Optional[FinancialMetrics] = None
    ) -> Optional[CommitteeAlert]:
        """
        Create a CommitteeAlert from rule evaluation result
        
        Args:
            rule: AlertRule that triggered
            property_id: Property ID
            period_id: Financial period ID
            evaluation_result: Result from AlertRulesService.evaluate_rule()
            metrics: FinancialMetrics object
        
        Returns:
            Created CommitteeAlert or None if duplicate
        """
        try:
            # Check for duplicate alert (same rule, property, period, active status)
            existing = self.db.query(CommitteeAlert).filter(
                CommitteeAlert.property_id == property_id,
                CommitteeAlert.financial_period_id == period_id,
                CommitteeAlert.status == AlertStatus.ACTIVE,
                CommitteeAlert.alert_metadata.contains({"rule_id": rule.id})
            ).first()
            
            if existing:
                logger.debug(
                    f"Duplicate alert prevented: rule {rule.id}, property {property_id}, period {period_id}"
                )
                return None
            
            # Map rule result to alert type
            alert_type = self._map_rule_to_alert_type(rule, evaluation_result)
            
            # Determine severity
            severity_str = evaluation_result.get("severity", "warning")
            try:
                severity = AlertSeverity(severity_str.upper())
            except ValueError:
                severity = AlertSeverity.WARNING
            
            # Generate title and description
            title = self._generate_alert_title(rule, evaluation_result)
            description = self._generate_alert_description(rule, evaluation_result, metrics)
            
            # Assign committee
            assigned_committee = self._assign_committee(alert_type, severity)
            
            # Create alert
            alert = CommitteeAlert(
                property_id=property_id,
                financial_period_id=period_id,
                alert_type=alert_type,
                severity=severity,
                status=AlertStatus.ACTIVE,
                title=title,
                description=description,
                threshold_value=evaluation_result.get("threshold_value"),
                actual_value=evaluation_result.get("actual_value"),
                threshold_unit=self._get_threshold_unit(rule.field_name),
                assigned_committee=assigned_committee,
                requires_approval=severity in [AlertSeverity.CRITICAL, AlertSeverity.URGENT],
                triggered_at=datetime.utcnow(),
                related_metric=rule.field_name,
                alert_metadata={
                    "rule_id": rule.id,
                    "rule_name": rule.rule_name,
                    "rule_type": rule.rule_type.value if rule.rule_type else None,
                    "condition": rule.condition.value if rule.condition else None,
                    "breach_magnitude": evaluation_result.get("breach_magnitude"),
                    "breach_percentage": evaluation_result.get("metadata", {}).get("breach_percentage"),
                    "evaluation_result": evaluation_result.get("metadata", {})
                }
            )
            
            self.db.add(alert)
            self.db.commit()
            self.db.refresh(alert)
            
            logger.info(
                f"Created alert {alert.id}: {alert.alert_type.value} - {alert.title} "
                f"(property {property_id}, period {period_id})"
            )
            
            # Send notifications (non-blocking)
            try:
                notification_service = AlertNotificationService(self.db)
                notification_service.notify_alert_created(alert)
            except Exception as e:
                logger.error(f"Error sending notifications for alert {alert.id}: {str(e)}")
                # Don't fail alert creation if notification fails
            
            # Create workflow lock for critical/urgent alerts that require approval
            if severity in [AlertSeverity.CRITICAL, AlertSeverity.URGENT] and alert.requires_approval:
                try:
                    self._create_workflow_lock_for_alert(alert)
                except Exception as e:
                    logger.error(f"Error creating workflow lock for alert {alert.id}: {str(e)}")
                    # Don't fail alert creation if lock creation fails
            
            return alert
        
        except Exception as e:
            logger.error(
                f"Error creating alert from rule {rule.id}: {str(e)}",
                exc_info=True
            )
            self.db.rollback()
            return None
    
    def _map_rule_to_alert_type(
        self,
        rule: AlertRule,
        evaluation_result: Dict[str, Any]
    ) -> AlertType:
        """
        Map rule configuration to AlertType enum
        
        Uses rule_expression if available, otherwise infers from field_name
        """
        # Check rule_expression for explicit alert_type
        if rule.rule_expression and "alert_type" in rule.rule_expression:
            try:
                return AlertType(rule.rule_expression["alert_type"])
            except ValueError:
                pass
        
        # Infer from field_name
        field_lower = rule.field_name.lower()
        condition_str = rule.condition if isinstance(rule.condition, str) else rule.condition.value if hasattr(rule.condition, 'value') else str(rule.condition)
        
        if "dscr" in field_lower or "debt_service" in field_lower:
            return AlertType.DSCR_BREACH
        elif "occupancy" in field_lower:
            if evaluation_result.get("breach_magnitude", 0) < -0.15:  # 15% below threshold
                return AlertType.OCCUPANCY_CRITICAL
            else:
                return AlertType.OCCUPANCY_WARNING
        elif "ltv" in field_lower or "loan_to_value" in field_lower:
            return AlertType.LTV_BREACH
        elif "debt_yield" in field_lower:
            return AlertType.DEBT_YIELD_BREACH
        elif "interest_coverage" in field_lower:
            return AlertType.INTEREST_COVERAGE_BREACH
        elif "break_even" in field_lower and "occupancy" in field_lower:
            return AlertType.BREAK_EVEN_OCCUPANCY_BREACH
        elif "cash_flow" in field_lower and evaluation_result.get("actual_value", 0) < 0:
            return AlertType.CASH_FLOW_NEGATIVE
        elif "revenue" in field_lower and condition_str == "percentage_change":
            return AlertType.REVENUE_DECLINE
        elif "expense" in field_lower and condition_str == "percentage_change":
            return AlertType.EXPENSE_SPIKE
        elif "liquidity" in field_lower or "current_ratio" in field_lower:
            return AlertType.LIQUIDITY_WARNING
        elif "debt_to_equity" in field_lower:
            return AlertType.DEBT_TO_EQUITY_BREACH
        elif "capex" in field_lower or "capital" in field_lower:
            return AlertType.CAPEX_THRESHOLD
        elif "rent_collection" in field_lower or "collection_rate" in field_lower:
            return AlertType.RENT_COLLECTION_RATE
        else:
            return AlertType.FINANCIAL_THRESHOLD
    
    def _generate_alert_title(
        self,
        rule: AlertRule,
        evaluation_result: Dict[str, Any]
    ) -> str:
        """Generate alert title"""
        field_display = rule.field_name.replace("_", " ").title()
        severity = evaluation_result.get("severity", "warning")
        condition_str = rule.condition if isinstance(rule.condition, str) else rule.condition.value if hasattr(rule.condition, 'value') else str(rule.condition)
        
        if condition_str == "less_than":
            return f"{field_display} Below Threshold - {severity.upper()}"
        elif condition_str == "greater_than":
            return f"{field_display} Exceeds Threshold - {severity.upper()}"
        else:
            return f"{field_display} Alert - {severity.upper()}"
    
    def _generate_alert_description(
        self,
        rule: AlertRule,
        evaluation_result: Dict[str, Any],
        metrics: Optional[FinancialMetrics]
    ) -> str:
        """Generate detailed alert description"""
        message = evaluation_result.get("message", "")
        
        if rule.description:
            description = f"{rule.description}\n\n{message}"
        else:
            description = message
        
        # Add context if available
        if metrics:
            property_name = getattr(metrics.property, "name", "Property") if hasattr(metrics, "property") else "Property"
            period_name = getattr(metrics.period, "period_name", "Period") if hasattr(metrics, "period") else "Period"
            description += f"\n\nProperty: {property_name}\nPeriod: {period_name}"
        
        return description
    
    def _assign_committee(
        self,
        alert_type: AlertType,
        severity: AlertSeverity
    ) -> CommitteeType:
        """
        Assign alert to appropriate committee based on type and severity
        """
        # Critical/Urgent alerts go to Executive Committee
        if severity in [AlertSeverity.CRITICAL, AlertSeverity.URGENT]:
            return CommitteeType.EXECUTIVE_COMMITTEE
        
        # Type-based assignment
        if alert_type in [
            AlertType.DSCR_BREACH,
            AlertType.DEBT_YIELD_BREACH,
            AlertType.INTEREST_COVERAGE_BREACH,
            AlertType.CASH_FLOW_NEGATIVE,
            AlertType.REVENUE_DECLINE,
            AlertType.EXPENSE_SPIKE
        ]:
            return CommitteeType.FINANCE_SUBCOMMITTEE
        
        elif alert_type in [
            AlertType.OCCUPANCY_WARNING,
            AlertType.OCCUPANCY_CRITICAL,
            AlertType.BREAK_EVEN_OCCUPANCY_BREACH,
            AlertType.RENT_COLLECTION_RATE
        ]:
            return CommitteeType.OCCUPANCY_SUBCOMMITTEE
        
        elif alert_type in [
            AlertType.LTV_BREACH,
            AlertType.LIQUIDITY_WARNING,
            AlertType.DEBT_TO_EQUITY_BREACH,
            AlertType.COVENANT_VIOLATION
        ]:
            return CommitteeType.RISK_COMMITTEE
        
        else:
            return CommitteeType.RISK_COMMITTEE
    
    def _get_threshold_unit(self, field_name: str) -> str:
        """Get threshold unit based on field name"""
        field_lower = field_name.lower()
        
        if "ratio" in field_lower or "dscr" in field_lower or "ltv" in field_lower or "coverage" in field_lower:
            return "ratio"
        elif "rate" in field_lower or "percentage" in field_lower or "occupancy" in field_lower:
            return "percentage"
        elif "yield" in field_lower:
            return "percentage"
        else:
            return "dollars"
    
    def _create_workflow_lock_for_alert(self, alert: CommitteeAlert) -> Optional[Dict]:
        """
        Create a workflow lock for a critical/urgent alert
        
        Args:
            alert: CommitteeAlert that requires a workflow lock
        
        Returns:
            Dict with lock creation result or None if lock not needed
        """
        try:
            # Only create locks for critical/urgent alerts that require approval
            if alert.severity not in [AlertSeverity.CRITICAL, AlertSeverity.URGENT]:
                return None
            
            if not alert.requires_approval:
                return None
            
            # Map alert type to lock reason
            lock_reason = self._map_alert_type_to_lock_reason(alert.alert_type)
            if not lock_reason:
                logger.debug(f"No lock reason mapped for alert type {alert.alert_type.value}")
                return None
            
            # Determine lock scope based on alert type and severity
            lock_scope = self._determine_lock_scope(alert.alert_type, alert.severity)
            
            # Map committee to approval committee string
            approval_committee = self._map_committee_to_string(alert.assigned_committee)
            
            # Create lock title and description
            lock_title = f"Lock: {alert.title}"
            lock_description = f"Workflow lock created automatically for alert: {alert.title}\n\n{alert.description}"
            
            # Use system user (1) as locked_by, or get from alert if available
            locked_by = 1  # System user
            
            # Create workflow lock
            lock_service = WorkflowLockService(self.db)
            result = lock_service.create_lock(
                property_id=alert.property_id,
                lock_reason=lock_reason,
                lock_scope=lock_scope,
                title=lock_title,
                description=lock_description,
                locked_by=locked_by,
                alert_id=alert.id,
                approval_committee=approval_committee,
                br_id=alert.br_id
            )
            
            if result.get("success"):
                logger.info(
                    f"Workflow lock {result['lock']['id']} created for alert {alert.id} "
                    f"(property {alert.property_id})"
                )
            else:
                # Log but don't fail - lock might already exist
                logger.debug(
                    f"Workflow lock creation skipped for alert {alert.id}: {result.get('error')}"
                )
            
            return result
        
        except Exception as e:
            logger.error(
                f"Error creating workflow lock for alert {alert.id}: {str(e)}",
                exc_info=True
            )
            return None
    
    def _map_alert_type_to_lock_reason(self, alert_type: AlertType) -> Optional[LockReason]:
        """Map alert type to workflow lock reason"""
        mapping = {
            AlertType.DSCR_BREACH: LockReason.DSCR_BREACH,
            AlertType.OCCUPANCY_WARNING: LockReason.OCCUPANCY_THRESHOLD,
            AlertType.OCCUPANCY_CRITICAL: LockReason.OCCUPANCY_THRESHOLD,
            AlertType.LTV_BREACH: LockReason.COVENANT_VIOLATION,
            AlertType.COVENANT_VIOLATION: LockReason.COVENANT_VIOLATION,
            AlertType.VARIANCE_BREACH: LockReason.VARIANCE_BREACH,
            AlertType.ANOMALY_DETECTED: LockReason.FINANCIAL_ANOMALY,
            AlertType.FINANCIAL_THRESHOLD: LockReason.FINANCIAL_ANOMALY,
            AlertType.DEBT_YIELD_BREACH: LockReason.COVENANT_VIOLATION,
            AlertType.INTEREST_COVERAGE_BREACH: LockReason.COVENANT_VIOLATION,
            AlertType.CASH_FLOW_NEGATIVE: LockReason.FINANCIAL_ANOMALY,
            AlertType.REVENUE_DECLINE: LockReason.FINANCIAL_ANOMALY,
            AlertType.EXPENSE_SPIKE: LockReason.FINANCIAL_ANOMALY,
            AlertType.LIQUIDITY_WARNING: LockReason.FINANCIAL_ANOMALY,
            AlertType.DEBT_TO_EQUITY_BREACH: LockReason.COVENANT_VIOLATION,
        }
        return mapping.get(alert_type, LockReason.COMMITTEE_REVIEW)
    
    def _determine_lock_scope(self, alert_type: AlertType, severity: AlertSeverity) -> LockScope:
        """Determine lock scope based on alert type and severity"""
        # Critical alerts lock all property operations
        if severity == AlertSeverity.CRITICAL:
            return LockScope.PROPERTY_ALL
        
        # Urgent alerts typically lock financial updates
        if severity == AlertSeverity.URGENT:
            return LockScope.FINANCIAL_UPDATES
        
        # Type-based scope for warnings
        financial_types = [
            AlertType.DSCR_BREACH,
            AlertType.CASH_FLOW_NEGATIVE,
            AlertType.REVENUE_DECLINE,
            AlertType.EXPENSE_SPIKE,
            AlertType.LIQUIDITY_WARNING,
            AlertType.DEBT_TO_EQUITY_BREACH,
            AlertType.DEBT_YIELD_BREACH,
            AlertType.INTEREST_COVERAGE_BREACH
        ]
        
        if alert_type in financial_types:
            return LockScope.FINANCIAL_UPDATES
        
        # Default to financial updates
        return LockScope.FINANCIAL_UPDATES
    
    def _map_committee_to_string(self, committee: CommitteeType) -> str:
        """Map CommitteeType enum to string for approval_committee field"""
        mapping = {
            CommitteeType.FINANCE_SUBCOMMITTEE: "Finance Sub-Committee",
            CommitteeType.OCCUPANCY_SUBCOMMITTEE: "Occupancy Sub-Committee",
            CommitteeType.RISK_COMMITTEE: "Risk Committee",
            CommitteeType.EXECUTIVE_COMMITTEE: "Executive Committee",
        }
        return mapping.get(committee, "Risk Committee")

