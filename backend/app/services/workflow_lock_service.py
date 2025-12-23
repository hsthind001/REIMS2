"""
Workflow Lock Service

Manages workflow locks, pauses, and committee approvals.
Enforces governance controls on property operations.
"""
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from datetime import datetime
import logging

from app.models.workflow_lock import WorkflowLock, LockReason, LockScope, LockStatus
from app.models.committee_alert import CommitteeAlert, AlertStatus, AlertType, AlertSeverity, CommitteeType
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.services.dscr_monitoring_service import DSCRMonitoringService
from decimal import Decimal

logger = logging.getLogger(__name__)


class WorkflowLockService:
    """
    Workflow Lock Management Service

    Handles:
    - Lock creation and release
    - Committee approval workflow
    - Auto-release based on conditions
    - Operation blocking checks
    """

    def __init__(self, db: Session):
        self.db = db

    def create_lock(
        self,
        property_id: int,
        lock_reason: LockReason,
        lock_scope: LockScope,
        title: str,
        description: str,
        locked_by: int,
        alert_id: Optional[int] = None,
        approval_committee: Optional[str] = None,
        auto_release_conditions: Optional[Dict] = None,
        br_id: Optional[str] = None,
    ) -> Dict:
        """
        Create a workflow lock
        """
        try:
            # Verify property exists
            property = self.db.query(Property).filter(Property.id == property_id).first()
            if not property:
                return {"success": False, "error": "Property not found"}

            # Check if similar active lock exists
            existing_lock = self.db.query(WorkflowLock).filter(
                WorkflowLock.property_id == property_id,
                WorkflowLock.lock_reason == lock_reason,
                WorkflowLock.status == LockStatus.ACTIVE
            ).first()

            if existing_lock:
                return {
                    "success": False,
                    "error": "Similar active lock already exists",
                    "lock_id": existing_lock.id
                }

            # Create lock
            lock = WorkflowLock(
                property_id=property_id,
                alert_id=alert_id,
                lock_reason=lock_reason,
                lock_scope=lock_scope,
                status=LockStatus.ACTIVE,
                title=title,
                description=description,
                requires_committee_approval=bool(approval_committee),
                approval_committee=approval_committee,
                locked_by=locked_by,
                auto_release_conditions=auto_release_conditions,
                br_id=br_id,
            )

            self.db.add(lock)
            self.db.commit()
            self.db.refresh(lock)

            logger.info(f"Workflow lock created: {lock.id} for property {property_id}")

            return {
                "success": True,
                "lock": lock.to_dict(),
                "message": f"Workflow lock created: {title}"
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create workflow lock: {str(e)}")
            return {"success": False, "error": str(e)}

    def release_lock(
        self,
        lock_id: int,
        unlocked_by: int,
        resolution_notes: Optional[str] = None,
        auto_released: bool = False
    ) -> Dict:
        """
        Release/unlock a workflow lock
        """
        try:
            lock = self.db.query(WorkflowLock).filter(WorkflowLock.id == lock_id).first()
            if not lock:
                return {"success": False, "error": "Lock not found"}

            if lock.status != LockStatus.ACTIVE:
                return {
                    "success": False,
                    "error": f"Lock is not active (current status: {lock.status.value})"
                }

            # Update lock
            lock.status = LockStatus.RELEASED
            lock.unlocked_at = datetime.utcnow()
            lock.unlocked_by = unlocked_by
            lock.resolution_notes = resolution_notes
            lock.auto_released = auto_released
            lock.updated_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(lock)

            logger.info(f"Workflow lock released: {lock_id}")

            return {
                "success": True,
                "lock": lock.to_dict(),
                "message": "Workflow lock released"
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to release workflow lock: {str(e)}")
            return {"success": False, "error": str(e)}

    def approve_lock(
        self,
        lock_id: int,
        approved_by: int,
        resolution_notes: str
    ) -> Dict:
        """
        Approve a lock (committee approval)
        """
        try:
            lock = self.db.query(WorkflowLock).filter(WorkflowLock.id == lock_id).first()
            if not lock:
                return {"success": False, "error": "Lock not found"}

            if not lock.requires_committee_approval:
                return {
                    "success": False,
                    "error": "This lock does not require committee approval"
                }

            # Update lock
            lock.status = LockStatus.APPROVED
            lock.approved_at = datetime.utcnow()
            lock.approved_by = approved_by
            lock.resolution_notes = resolution_notes
            lock.updated_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(lock)

            # Also resolve associated alert if exists
            if lock.alert_id:
                alert = self.db.query(CommitteeAlert).filter(
                    CommitteeAlert.id == lock.alert_id
                ).first()
                if alert and alert.status == AlertStatus.ACTIVE:
                    alert.status = AlertStatus.RESOLVED
                    alert.resolved_at = datetime.utcnow()
                    alert.resolved_by = approved_by
                    alert.resolution_notes = f"Approved via workflow lock: {resolution_notes}"
                    self.db.commit()

            logger.info(f"Workflow lock approved: {lock_id} by user {approved_by}")

            return {
                "success": True,
                "lock": lock.to_dict(),
                "message": "Workflow lock approved by committee"
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to approve workflow lock: {str(e)}")
            return {"success": False, "error": str(e)}

    def reject_lock(
        self,
        lock_id: int,
        rejected_by: int,
        rejection_reason: str
    ) -> Dict:
        """
        Reject a lock (committee rejection)
        """
        try:
            lock = self.db.query(WorkflowLock).filter(WorkflowLock.id == lock_id).first()
            if not lock:
                return {"success": False, "error": "Lock not found"}

            # Update lock
            lock.status = LockStatus.REJECTED
            lock.rejected_at = datetime.utcnow()
            lock.rejected_by = rejected_by
            lock.rejection_reason = rejection_reason
            lock.updated_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(lock)

            logger.info(f"Workflow lock rejected: {lock_id} by user {rejected_by}")

            return {
                "success": True,
                "lock": lock.to_dict(),
                "message": "Workflow lock rejected by committee"
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to reject workflow lock: {str(e)}")
            return {"success": False, "error": str(e)}

    def check_operation_allowed(
        self,
        property_id: int,
        operation: str
    ) -> Dict:
        """
        Check if an operation is allowed on a property

        Operations: "financial_update", "report_generation", "data_entry", "transaction"

        Returns:
        {
            "allowed": bool,
            "blocking_locks": [...],
            "reason": str
        }
        """
        # Get active locks for property
        active_locks = self.db.query(WorkflowLock).filter(
            WorkflowLock.property_id == property_id,
            WorkflowLock.status == LockStatus.ACTIVE
        ).all()

        blocking_locks = []
        for lock in active_locks:
            if lock.is_blocking(operation):
                blocking_locks.append(lock.to_dict())

        if blocking_locks:
            return {
                "allowed": False,
                "blocking_locks": blocking_locks,
                "reason": f"Operation '{operation}' is blocked by {len(blocking_locks)} active workflow lock(s)",
                "message": f"Property has active locks. Committee approval required."
            }

        return {
            "allowed": True,
            "blocking_locks": [],
            "reason": "No blocking locks found"
        }

    def get_property_locks(
        self,
        property_id: int,
        status: Optional[LockStatus] = None
    ) -> List[Dict]:
        """
        Get all locks for a property
        """
        query = self.db.query(WorkflowLock).filter(
            WorkflowLock.property_id == property_id
        )

        if status:
            query = query.filter(WorkflowLock.status == status)

        locks = query.order_by(WorkflowLock.locked_at.desc()).all()

        return [lock.to_dict() for lock in locks]

    def get_pending_approvals(
        self,
        committee: Optional[str] = None
    ) -> List[Dict]:
        """
        Get all locks pending committee approval
        """
        query = self.db.query(WorkflowLock).filter(
            WorkflowLock.status == LockStatus.ACTIVE,
            WorkflowLock.requires_committee_approval == True
        )

        if committee:
            query = query.filter(WorkflowLock.approval_committee == committee)

        locks = query.order_by(WorkflowLock.locked_at).all()

        return [lock.to_dict() for lock in locks]

    def check_auto_release_conditions(self, lock_id: int) -> Dict:
        """
        Check if a lock meets auto-release conditions

        Example conditions:
        {
            "metric": "DSCR",
            "threshold": 1.25,
            "operator": ">="
        }
        
        For DSCR locks, automatically checks if current DSCR has improved above threshold.
        """
        try:
            lock = self.db.query(WorkflowLock).filter(WorkflowLock.id == lock_id).first()
            if not lock:
                return {"success": False, "error": "Lock not found"}

            if not lock.auto_release_conditions:
                return {"success": False, "error": "No auto-release conditions defined"}

            conditions = lock.auto_release_conditions
            metric = conditions.get("metric")
            threshold = conditions.get("threshold")
            operator = conditions.get("operator", ">=")
            
            conditions_met = False
            current_value = None
            message = "Auto-release conditions not yet met"

            # Check DSCR-based conditions
            if metric == "DSCR" and threshold is not None:
                try:
                    # Get latest period for the property
                    period = self.db.query(FinancialPeriod).filter(
                        FinancialPeriod.property_id == lock.property_id
                    ).order_by(FinancialPeriod.period_end_date.desc()).first()
                    
                    if not period:
                        return {
                            "success": True,
                            "conditions_met": False,
                            "message": "No financial period found for DSCR calculation"
                        }
                    
                    # Calculate current DSCR
                    dscr_service = DSCRMonitoringService(self.db)
                    dscr_result = dscr_service.calculate_dscr(lock.property_id, period.id)
                    
                    if dscr_result.get("success"):
                        current_value = float(dscr_result["dscr"])
                        
                        # Check condition based on operator
                        if operator == ">=":
                            conditions_met = current_value >= float(threshold)
                        elif operator == ">":
                            conditions_met = current_value > float(threshold)
                        elif operator == "<=":
                            conditions_met = current_value <= float(threshold)
                        elif operator == "<":
                            conditions_met = current_value < float(threshold)
                        elif operator == "==":
                            conditions_met = abs(current_value - float(threshold)) < 0.01  # Small tolerance
                        else:
                            logger.warning(f"Unknown operator '{operator}' in auto-release conditions")
                            conditions_met = False
                        
                        if conditions_met:
                            message = f"Auto-release condition met: DSCR {current_value:.2f} {operator} {threshold}"
                        else:
                            message = f"DSCR {current_value:.2f} does not meet condition ({operator} {threshold})"
                    else:
                        message = f"Failed to calculate DSCR: {dscr_result.get('error', 'Unknown error')}"
                        
                except Exception as e:
                    logger.error(f"Error checking DSCR condition for lock {lock_id}: {str(e)}")
                    return {
                        "success": False,
                        "error": f"Failed to check DSCR condition: {str(e)}"
                    }
            else:
                # Unknown metric type
                logger.warning(f"Unknown metric type '{metric}' in auto-release conditions for lock {lock_id}")
                return {
                    "success": False,
                    "error": f"Unsupported metric type: {metric}"
                }

            if conditions_met:
                # Auto-release the lock
                result = self.release_lock(
                    lock_id=lock_id,
                    unlocked_by=1,  # System user
                    resolution_notes=f"Auto-released: {message}",
                    auto_released=True
                )
                result["current_value"] = current_value
                result["threshold"] = threshold
                return result

            return {
                "success": True,
                "conditions_met": False,
                "message": message,
                "current_value": current_value,
                "threshold": threshold
            }

        except Exception as e:
            logger.error(f"Failed to check auto-release conditions: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_lock_statistics(self) -> Dict:
        """
        Get statistics about workflow locks across all properties
        """
        try:
            # Use func.count with specific columns to avoid loading all model columns
            from sqlalchemy import func
            total_locks = self.db.query(func.count(WorkflowLock.id)).scalar() or 0
            active_locks = self.db.query(func.count(WorkflowLock.id)).filter(
                WorkflowLock.status == LockStatus.ACTIVE
            ).scalar() or 0
            pending_approvals = self.db.query(func.count(WorkflowLock.id)).filter(
                WorkflowLock.status == LockStatus.ACTIVE,
                WorkflowLock.requires_committee_approval == True
            ).scalar() or 0

            # Get locks by reason
            locks_by_reason = {}
            for reason in LockReason:
                count = self.db.query(func.count(WorkflowLock.id)).filter(
                    WorkflowLock.lock_reason == reason,
                    WorkflowLock.status == LockStatus.ACTIVE
                ).scalar() or 0
                if count > 0:
                    locks_by_reason[reason.value] = count

            return {
                "total_locks": total_locks,
                "active_locks": active_locks,
                "pending_approvals": pending_approvals,
                "locks_by_reason": locks_by_reason,
            }
        except Exception as e:
            # If there's a schema mismatch, return default values
            logger.warning(f"Error getting lock statistics (possibly schema mismatch): {e}")
            return {
                "total_locks": 0,
                "active_locks": 0,
                "pending_approvals": 0,
                "locks_by_reason": {},
            }

    def pause_property_operations(
        self,
        property_id: int,
        reason: str,
        locked_by: int
    ) -> Dict:
        """
        Convenience method to pause all operations on a property
        """
        return self.create_lock(
            property_id=property_id,
            lock_reason=LockReason.MANUAL_HOLD,
            lock_scope=LockScope.PROPERTY_ALL,
            title="Property Operations Paused",
            description=reason,
            locked_by=locked_by,
            approval_committee="Executive Committee",
        )

    def resume_property_operations(
        self,
        property_id: int,
        unlocked_by: int,
        resolution_notes: str
    ) -> Dict:
        """
        Convenience method to resume all operations on a property
        """
        # Get active locks for property
        active_locks = self.db.query(WorkflowLock).filter(
            WorkflowLock.property_id == property_id,
            WorkflowLock.status == LockStatus.ACTIVE
        ).all()

        results = []
        for lock in active_locks:
            result = self.release_lock(
                lock_id=lock.id,
                unlocked_by=unlocked_by,
                resolution_notes=resolution_notes
            )
            results.append(result)

        return {
            "success": True,
            "locks_released": len(results),
            "results": results
        }
    
    def create_lock_from_alert(
        self,
        alert: CommitteeAlert,
        locked_by: int = 1  # Default to system user
    ) -> Dict:
        """
        Create a workflow lock from a CommitteeAlert
        
        Automatically determines lock reason, scope, and committee based on alert.
        Handles duplicate lock prevention.
        
        Args:
            alert: CommitteeAlert to create lock for
            locked_by: User ID who is creating the lock (default: system user)
        
        Returns:
            Dict with lock creation result
        """
        try:
            # Only create locks for critical/urgent alerts that require approval
            if alert.severity not in [AlertSeverity.CRITICAL, AlertSeverity.URGENT]:
                return {
                    "success": False,
                    "error": "Only critical/urgent alerts require workflow locks"
                }
            
            if not alert.requires_approval:
                return {
                    "success": False,
                    "error": "Alert does not require approval"
                }
            
            # Check if lock already exists for this alert
            existing_lock = self.db.query(WorkflowLock).filter(
                WorkflowLock.alert_id == alert.id,
                WorkflowLock.status == LockStatus.ACTIVE
            ).first()
            
            if existing_lock:
                return {
                    "success": False,
                    "error": "Workflow lock already exists for this alert",
                    "lock_id": existing_lock.id
                }
            
            # Map alert type to lock reason
            lock_reason = self._map_alert_type_to_lock_reason(alert.alert_type)
            
            # Determine lock scope
            lock_scope = self._determine_lock_scope(alert.alert_type, alert.severity)
            
            # Map committee to approval committee string
            approval_committee = self._map_committee_to_string(alert.assigned_committee)
            
            # Create lock title and description
            lock_title = f"Lock: {alert.title}"
            lock_description = (
                f"Workflow lock created automatically for alert: {alert.title}\n\n"
                f"{alert.description}"
            )
            
            # Create the lock
            return self.create_lock(
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
        
        except Exception as e:
            logger.error(f"Error creating lock from alert {alert.id}: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _map_alert_type_to_lock_reason(self, alert_type: AlertType) -> LockReason:
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
