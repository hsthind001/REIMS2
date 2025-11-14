"""
DSCR (Debt Service Coverage Ratio) Monitoring Service

Calculates and monitors DSCR for covenant compliance.
Triggers alerts and workflow locks when thresholds are breached.

DSCR = Net Operating Income (NOI) / Total Debt Service
- DSCR >= 1.25: Healthy
- DSCR 1.10 - 1.25: Warning
- DSCR < 1.10: Critical
"""
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import logging

from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.financial_metrics import FinancialMetrics
from app.models.income_statement_data import IncomeStatementData
from app.models.committee_alert import CommitteeAlert, AlertType, AlertSeverity, AlertStatus, CommitteeType
from app.models.workflow_lock import WorkflowLock, LockReason, LockScope, LockStatus

logger = logging.getLogger(__name__)


class DSCRMonitoringService:
    """
    DSCR Monitoring and Covenant Compliance Service
    """

    # DSCR Thresholds
    CRITICAL_THRESHOLD = Decimal("1.10")  # Below this = critical
    WARNING_THRESHOLD = Decimal("1.25")   # Below this = warning
    HEALTHY_THRESHOLD = Decimal("1.25")   # Above this = healthy

    def __init__(self, db: Session):
        self.db = db

    def calculate_dscr(
        self,
        property_id: int,
        financial_period_id: Optional[int] = None
    ) -> Dict:
        """
        Calculate DSCR for a property and period

        DSCR = Net Operating Income (NOI) / Total Debt Service

        Returns:
        {
            "dscr": Decimal,
            "noi": Decimal,
            "total_debt_service": Decimal,
            "status": "healthy" | "warning" | "critical",
            "period": {...}
        }
        """
        try:
            # Get property
            property = self.db.query(Property).filter(Property.id == property_id).first()
            if not property:
                return {"success": False, "error": "Property not found"}

            # Get financial period (latest if not specified)
            if financial_period_id:
                period = self.db.query(FinancialPeriod).filter(
                    FinancialPeriod.id == financial_period_id
                ).first()
            else:
                period = self.db.query(FinancialPeriod).filter(
                    FinancialPeriod.property_id == property_id
                ).order_by(FinancialPeriod.period_end_date.desc()).first()

            if not period:
                return {"success": False, "error": "No financial period found"}

            # Calculate NOI
            noi = self._calculate_noi(property_id, period.id)

            # Get total debt service
            total_debt_service = self._get_total_debt_service(property_id, period.id)

            if total_debt_service == 0:
                return {
                    "success": False,
                    "error": "Total debt service is zero - cannot calculate DSCR"
                }

            # Calculate DSCR
            dscr = noi / total_debt_service

            # Determine status
            if dscr < self.CRITICAL_THRESHOLD:
                status = "critical"
                severity = AlertSeverity.CRITICAL
            elif dscr < self.WARNING_THRESHOLD:
                status = "warning"
                severity = AlertSeverity.WARNING
            else:
                status = "healthy"
                severity = None

            result = {
                "success": True,
                "dscr": float(dscr),
                "noi": float(noi),
                "total_debt_service": float(total_debt_service),
                "status": status,
                "severity": severity.value if severity else None,
                "threshold_breached": dscr < self.WARNING_THRESHOLD,
                "property": {
                    "id": property.id,
                    "name": property.property_name,
                    "code": property.property_code,
                },
                "period": {
                    "id": period.id,
                    "start_date": period.period_start_date.isoformat(),
                    "end_date": period.period_end_date.isoformat(),
                    "period_type": period.period_type,
                },
                "calculated_at": datetime.utcnow().isoformat(),
            }

            # Check if alert needed
            if dscr < self.WARNING_THRESHOLD:
                alert = self._create_dscr_alert(
                    property_id=property_id,
                    financial_period_id=period.id,
                    dscr=dscr,
                    noi=noi,
                    total_debt_service=total_debt_service,
                    severity=severity,
                )
                result["alert_created"] = True
                result["alert_id"] = alert.id

            return result

        except Exception as e:
            logger.error(f"DSCR calculation failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def _calculate_noi(self, property_id: int, financial_period_id: int) -> Decimal:
        """
        Calculate Net Operating Income (NOI)

        NOI = Total Revenue - Operating Expenses
        """
        # Get income statement data for the period
        income_data = self.db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.financial_period_id == financial_period_id
        ).all()

        total_revenue = Decimal("0")
        operating_expenses = Decimal("0")

        for item in income_data:
            # Revenue accounts (typically 4xxxx or similar)
            if item.account_code and item.account_code.startswith("4"):
                total_revenue += Decimal(str(item.amount or 0))
            # Operating expense accounts (typically 5xxxx or 6xxxx)
            elif item.account_code and (
                item.account_code.startswith("5") or
                item.account_code.startswith("6")
            ):
                operating_expenses += Decimal(str(item.amount or 0))

        noi = total_revenue - operating_expenses
        return noi

    def _get_total_debt_service(
        self,
        property_id: int,
        financial_period_id: int
    ) -> Decimal:
        """
        Get total debt service (principal + interest payments)

        For now, we'll look for debt service in income statement or use a mock value.
        In production, this should come from a separate loan/debt table.
        """
        # Look for debt service accounts in income statement
        debt_accounts = self.db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.financial_period_id == financial_period_id,
            IncomeStatementData.account_code.like("7%")  # Debt service accounts
        ).all()

        total_debt_service = Decimal("0")
        for account in debt_accounts:
            total_debt_service += Decimal(str(account.amount or 0))

        # If no debt service found, use mock value for demo
        if total_debt_service == 0:
            # Mock: 8% of NOI (typical for commercial real estate)
            noi = self._calculate_noi(property_id, financial_period_id)
            total_debt_service = noi * Decimal("0.80")  # Assuming 80% of NOI goes to debt

        return total_debt_service

    def _create_dscr_alert(
        self,
        property_id: int,
        financial_period_id: int,
        dscr: Decimal,
        noi: Decimal,
        total_debt_service: Decimal,
        severity: AlertSeverity,
    ) -> CommitteeAlert:
        """
        Create a DSCR breach alert
        """
        # Check if alert already exists for this property/period
        existing_alert = self.db.query(CommitteeAlert).filter(
            CommitteeAlert.property_id == property_id,
            CommitteeAlert.financial_period_id == financial_period_id,
            CommitteeAlert.alert_type == AlertType.DSCR_BREACH,
            CommitteeAlert.status == AlertStatus.ACTIVE
        ).first()

        if existing_alert:
            # Update existing alert
            existing_alert.actual_value = dscr
            existing_alert.severity = severity
            existing_alert.updated_at = datetime.utcnow()
            self.db.commit()
            return existing_alert

        # Create new alert
        alert = CommitteeAlert(
            property_id=property_id,
            financial_period_id=financial_period_id,
            alert_type=AlertType.DSCR_BREACH,
            severity=severity,
            status=AlertStatus.ACTIVE,
            title=f"DSCR Breach: {float(dscr):.2f}",
            description=f"Debt Service Coverage Ratio ({float(dscr):.2f}) is below the threshold of {float(self.WARNING_THRESHOLD)}.\n\n"
                       f"NOI: ${float(noi):,.2f}\n"
                       f"Total Debt Service: ${float(total_debt_service):,.2f}\n"
                       f"DSCR: {float(dscr):.2f}\n\n"
                       f"This may indicate covenant violation. Finance committee review required.",
            threshold_value=self.WARNING_THRESHOLD,
            actual_value=dscr,
            threshold_unit="ratio",
            assigned_committee=CommitteeType.FINANCE_SUBCOMMITTEE,
            requires_approval=True,
            related_metric="DSCR",
            br_id="BR-003",
            metadata={
                "noi": float(noi),
                "total_debt_service": float(total_debt_service),
                "calculation_date": datetime.utcnow().isoformat(),
            }
        )

        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)

        # Create workflow lock if critical
        if severity == AlertSeverity.CRITICAL:
            self._create_workflow_lock(alert)

        logger.info(f"DSCR alert created: {alert.id} for property {property_id}")
        return alert

    def _create_workflow_lock(self, alert: CommitteeAlert):
        """
        Create workflow lock when DSCR is critical
        """
        # Check if lock already exists
        existing_lock = self.db.query(WorkflowLock).filter(
            WorkflowLock.alert_id == alert.id,
            WorkflowLock.status == LockStatus.ACTIVE
        ).first()

        if existing_lock:
            return existing_lock

        lock = WorkflowLock(
            property_id=alert.property_id,
            alert_id=alert.id,
            lock_reason=LockReason.DSCR_BREACH,
            lock_scope=LockScope.FINANCIAL_UPDATES,
            status=LockStatus.ACTIVE,
            title=f"DSCR Critical: Financial Updates Locked",
            description=f"Property locked due to critical DSCR breach ({float(alert.actual_value):.2f}). "
                       f"Finance committee approval required before financial updates can proceed.",
            requires_committee_approval=True,
            approval_committee="Finance Sub-Committee",
            locked_by=1,  # System user
            br_id="BR-003",
            metadata={
                "dscr": float(alert.actual_value),
                "threshold": float(alert.threshold_value),
                "alert_id": alert.id,
            }
        )

        self.db.add(lock)
        self.db.commit()
        self.db.refresh(lock)

        logger.info(f"Workflow lock created: {lock.id} for alert {alert.id}")
        return lock

    def monitor_all_properties(self, lookback_days: int = 90) -> Dict:
        """
        Monitor DSCR for all active properties

        Returns summary of properties with DSCR issues
        """
        results = {
            "total_properties": 0,
            "healthy": 0,
            "warning": 0,
            "critical": 0,
            "properties": [],
        }

        # Get all active properties
        properties = self.db.query(Property).filter(
            Property.status == "active"
        ).all()

        results["total_properties"] = len(properties)

        for property in properties:
            dscr_result = self.calculate_dscr(property.id)

            if dscr_result.get("success"):
                status = dscr_result["status"]

                if status == "healthy":
                    results["healthy"] += 1
                elif status == "warning":
                    results["warning"] += 1
                elif status == "critical":
                    results["critical"] += 1

                results["properties"].append({
                    "property_id": property.id,
                    "property_name": property.property_name,
                    "dscr": dscr_result.get("dscr"),
                    "status": status,
                    "alert_created": dscr_result.get("alert_created", False),
                })

        return results

    def get_dscr_history(
        self,
        property_id: int,
        limit: int = 12
    ) -> List[Dict]:
        """
        Get DSCR history for a property (last N periods)
        """
        periods = self.db.query(FinancialPeriod).filter(
            FinancialPeriod.property_id == property_id
        ).order_by(FinancialPeriod.period_end_date.desc()).limit(limit).all()

        history = []
        for period in reversed(periods):
            result = self.calculate_dscr(property_id, period.id)
            if result.get("success"):
                history.append({
                    "period": period.period_end_date.isoformat(),
                    "dscr": result["dscr"],
                    "status": result["status"],
                    "noi": result["noi"],
                    "total_debt_service": result["total_debt_service"],
                })

        return history

    def get_covenant_status(self, property_id: int) -> Dict:
        """
        Get covenant compliance status for a property
        """
        dscr_result = self.calculate_dscr(property_id)

        if not dscr_result.get("success"):
            return dscr_result

        dscr = Decimal(str(dscr_result["dscr"]))

        # Check for active alerts
        active_alerts = self.db.query(CommitteeAlert).filter(
            CommitteeAlert.property_id == property_id,
            CommitteeAlert.alert_type == AlertType.DSCR_BREACH,
            CommitteeAlert.status == AlertStatus.ACTIVE
        ).count()

        # Check for workflow locks
        active_locks = self.db.query(WorkflowLock).filter(
            WorkflowLock.property_id == property_id,
            WorkflowLock.lock_reason == LockReason.DSCR_BREACH,
            WorkflowLock.status == LockStatus.ACTIVE
        ).count()

        return {
            "success": True,
            "property_id": property_id,
            "dscr": float(dscr),
            "covenant_compliant": dscr >= self.WARNING_THRESHOLD,
            "status": dscr_result["status"],
            "active_alerts": active_alerts,
            "active_locks": active_locks,
            "thresholds": {
                "healthy": float(self.HEALTHY_THRESHOLD),
                "warning": float(self.WARNING_THRESHOLD),
                "critical": float(self.CRITICAL_THRESHOLD),
            }
        }
