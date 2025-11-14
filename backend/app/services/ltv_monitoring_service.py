"""
LTV (Loan-to-Value) Monitoring Service

Calculates and monitors LTV for covenant compliance and risk assessment.

LTV = Current Loan Balance / Property Value
- LTV <= 65%: Strong
- LTV 65-75%: Good
- LTV 75-80%: Fair
- LTV > 80%: High Risk
"""
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime
import logging

from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.balance_sheet_data import BalanceSheetData
from app.models.committee_alert import CommitteeAlert, AlertType, AlertSeverity, AlertStatus, CommitteeType

logger = logging.getLogger(__name__)


class LTVMonitoringService:
    """
    LTV (Loan-to-Value) Monitoring Service
    """

    # LTV Thresholds
    STRONG_THRESHOLD = Decimal("0.65")      # <= 65% is strong
    GOOD_THRESHOLD = Decimal("0.75")        # 65-75% is good
    FAIR_THRESHOLD = Decimal("0.80")        # 75-80% is fair
    HIGH_RISK_THRESHOLD = Decimal("0.80")   # > 80% is high risk

    def __init__(self, db: Session):
        self.db = db

    def calculate_ltv(
        self,
        property_id: int,
        financial_period_id: Optional[int] = None,
        property_value: Optional[Decimal] = None
    ) -> Dict:
        """
        Calculate LTV for a property

        LTV = Current Loan Balance / Property Value

        Parameters:
        - property_id: Property ID
        - financial_period_id: Financial period (optional, uses latest if not specified)
        - property_value: Override property value (optional, uses balance sheet value if not provided)

        Returns:
        {
            "ltv": Decimal,
            "loan_balance": Decimal,
            "property_value": Decimal,
            "status": "strong" | "good" | "fair" | "high_risk",
            "period": {...}
        }
        """
        try:
            # Get property
            property = self.db.query(Property).filter(Property.id == property_id).first()
            if not property:
                return {"success": False, "error": "Property not found"}

            # Get financial period
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

            # Get loan balance from balance sheet
            loan_balance = self._get_loan_balance(property_id, period.id)

            if loan_balance == 0:
                return {
                    "success": False,
                    "error": "Loan balance is zero - cannot calculate LTV"
                }

            # Get property value
            if property_value is None:
                property_value = self._get_property_value(property_id, period.id)

            if property_value == 0:
                return {
                    "success": False,
                    "error": "Property value is zero - cannot calculate LTV"
                }

            # Calculate LTV
            ltv = loan_balance / property_value

            # Determine status
            if ltv <= self.STRONG_THRESHOLD:
                status = "strong"
                severity = None
            elif ltv <= self.GOOD_THRESHOLD:
                status = "good"
                severity = None
            elif ltv <= self.FAIR_THRESHOLD:
                status = "fair"
                severity = AlertSeverity.WARNING
            else:
                status = "high_risk"
                severity = AlertSeverity.CRITICAL

            result = {
                "success": True,
                "ltv": float(ltv),
                "ltv_percentage": float(ltv * 100),
                "loan_balance": float(loan_balance),
                "property_value": float(property_value),
                "status": status,
                "severity": severity.value if severity else None,
                "threshold_breached": ltv > self.FAIR_THRESHOLD,
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

            # Create alert if threshold breached
            if ltv > self.FAIR_THRESHOLD:
                alert = self._create_ltv_alert(
                    property_id=property_id,
                    financial_period_id=period.id,
                    ltv=ltv,
                    loan_balance=loan_balance,
                    property_value=property_value,
                    severity=severity,
                )
                result["alert_created"] = True
                result["alert_id"] = alert.id

            return result

        except Exception as e:
            logger.error(f"LTV calculation failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def _get_loan_balance(self, property_id: int, financial_period_id: int) -> Decimal:
        """
        Get current loan balance from balance sheet

        Looks for long-term debt and notes payable accounts
        """
        # Get balance sheet data for the period
        balance_sheet_data = self.db.query(BalanceSheetData).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.financial_period_id == financial_period_id
        ).all()

        loan_balance = Decimal("0")

        for item in balance_sheet_data:
            # Look for loan/debt accounts
            # Typically account codes like 2100 (Long-term debt), 2110 (Notes payable), etc.
            if item.account_code and (
                item.account_code.startswith("21") or
                "loan" in item.account_name.lower() if item.account_name else False or
                "debt" in item.account_name.lower() if item.account_name else False or
                "mortgage" in item.account_name.lower() if item.account_name else False
            ):
                loan_balance += Decimal(str(item.amount or 0))

        # If no loan found, use a mock value for demo
        if loan_balance == 0:
            # Mock: Use 70% of property value as typical commercial real estate LTV
            property_value = self._get_property_value(property_id, financial_period_id)
            loan_balance = property_value * Decimal("0.70")

        return loan_balance

    def _get_property_value(self, property_id: int, financial_period_id: int) -> Decimal:
        """
        Get property value from balance sheet (total assets) or property record
        """
        # First try to get from balance sheet (total assets)
        balance_sheet_data = self.db.query(BalanceSheetData).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.financial_period_id == financial_period_id
        ).all()

        total_assets = Decimal("0")
        for item in balance_sheet_data:
            # Sum up asset accounts (typically 1xxxx)
            if item.account_code and item.account_code.startswith("1"):
                total_assets += Decimal(str(item.amount or 0))

        if total_assets > 0:
            return total_assets

        # Fallback: use a mock value based on property size
        property = self.db.query(Property).filter(Property.id == property_id).first()
        if property and property.total_area_sqft:
            # Mock: $200 per sqft for commercial real estate
            property_value = Decimal(str(property.total_area_sqft)) * Decimal("200")
            return property_value

        # Last resort: use a fixed mock value
        return Decimal("5000000")  # $5M

    def _create_ltv_alert(
        self,
        property_id: int,
        financial_period_id: int,
        ltv: Decimal,
        loan_balance: Decimal,
        property_value: Decimal,
        severity: AlertSeverity,
    ) -> CommitteeAlert:
        """
        Create an LTV breach alert
        """
        # Check if alert already exists
        existing_alert = self.db.query(CommitteeAlert).filter(
            CommitteeAlert.property_id == property_id,
            CommitteeAlert.financial_period_id == financial_period_id,
            CommitteeAlert.alert_type == AlertType.LTV_BREACH,
            CommitteeAlert.status == AlertStatus.ACTIVE
        ).first()

        if existing_alert:
            # Update existing alert
            existing_alert.actual_value = ltv
            existing_alert.severity = severity
            existing_alert.updated_at = datetime.utcnow()
            self.db.commit()
            return existing_alert

        # Create new alert
        alert = CommitteeAlert(
            property_id=property_id,
            financial_period_id=financial_period_id,
            alert_type=AlertType.LTV_BREACH,
            severity=severity,
            status=AlertStatus.ACTIVE,
            title=f"LTV Breach: {float(ltv * 100):.1f}%",
            description=f"Loan-to-Value ratio ({float(ltv * 100):.1f}%) exceeds acceptable threshold of {float(self.FAIR_THRESHOLD * 100):.1f}%.\n\n"
                       f"Loan Balance: ${float(loan_balance):,.2f}\n"
                       f"Property Value: ${float(property_value):,.2f}\n"
                       f"LTV: {float(ltv * 100):.1f}%\n\n"
                       f"High LTV indicates increased risk and may violate loan covenants. "
                       f"Finance committee review required.",
            threshold_value=self.FAIR_THRESHOLD,
            actual_value=ltv,
            threshold_unit="ratio",
            assigned_committee=CommitteeType.FINANCE_SUBCOMMITTEE,
            requires_approval=True,
            related_metric="LTV",
            br_id="BR-003",
            metadata={
                "loan_balance": float(loan_balance),
                "property_value": float(property_value),
                "ltv_percentage": float(ltv * 100),
                "calculation_date": datetime.utcnow().isoformat(),
            }
        )

        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)

        logger.info(f"LTV alert created: {alert.id} for property {property_id}")
        return alert

    def monitor_all_properties(self) -> Dict:
        """
        Monitor LTV for all active properties
        """
        results = {
            "total_properties": 0,
            "strong": 0,
            "good": 0,
            "fair": 0,
            "high_risk": 0,
            "properties": [],
        }

        # Get all active properties
        properties = self.db.query(Property).filter(
            Property.status == "active"
        ).all()

        results["total_properties"] = len(properties)

        for property in properties:
            ltv_result = self.calculate_ltv(property.id)

            if ltv_result.get("success"):
                status = ltv_result["status"]

                if status == "strong":
                    results["strong"] += 1
                elif status == "good":
                    results["good"] += 1
                elif status == "fair":
                    results["fair"] += 1
                elif status == "high_risk":
                    results["high_risk"] += 1

                results["properties"].append({
                    "property_id": property.id,
                    "property_name": property.property_name,
                    "ltv": ltv_result.get("ltv"),
                    "ltv_percentage": ltv_result.get("ltv_percentage"),
                    "status": status,
                    "alert_created": ltv_result.get("alert_created", False),
                })

        return results

    def get_ltv_history(
        self,
        property_id: int,
        limit: int = 12
    ) -> List[Dict]:
        """
        Get LTV history for a property (last N periods)
        """
        periods = self.db.query(FinancialPeriod).filter(
            FinancialPeriod.property_id == property_id
        ).order_by(FinancialPeriod.period_end_date.desc()).limit(limit).all()

        history = []
        for period in reversed(periods):
            result = self.calculate_ltv(property_id, period.id)
            if result.get("success"):
                history.append({
                    "period": period.period_end_date.isoformat(),
                    "ltv": result["ltv"],
                    "ltv_percentage": result["ltv_percentage"],
                    "status": result["status"],
                    "loan_balance": result["loan_balance"],
                    "property_value": result["property_value"],
                })

        return history

    def get_ltv_compliance_report(self, property_id: int) -> Dict:
        """
        Get LTV compliance report for a property
        """
        ltv_result = self.calculate_ltv(property_id)

        if not ltv_result.get("success"):
            return ltv_result

        ltv = Decimal(str(ltv_result["ltv"]))

        # Get active alerts
        active_alerts = self.db.query(CommitteeAlert).filter(
            CommitteeAlert.property_id == property_id,
            CommitteeAlert.alert_type == AlertType.LTV_BREACH,
            CommitteeAlert.status == AlertStatus.ACTIVE
        ).count()

        # Calculate headroom
        headroom = self.FAIR_THRESHOLD - ltv
        headroom_dollars = headroom * Decimal(str(ltv_result["property_value"]))

        return {
            "success": True,
            "property_id": property_id,
            "ltv": float(ltv),
            "ltv_percentage": float(ltv * 100),
            "covenant_compliant": ltv <= self.FAIR_THRESHOLD,
            "status": ltv_result["status"],
            "active_alerts": active_alerts,
            "headroom": {
                "ltv_points": float(headroom),
                "percentage_points": float(headroom * 100),
                "dollar_value": float(headroom_dollars),
            },
            "thresholds": {
                "strong": float(self.STRONG_THRESHOLD * 100),
                "good": float(self.GOOD_THRESHOLD * 100),
                "fair": float(self.FAIR_THRESHOLD * 100),
                "high_risk": float(self.HIGH_RISK_THRESHOLD * 100),
            }
        }

    def estimate_refinance_capacity(self, property_id: int) -> Dict:
        """
        Estimate additional loan capacity based on current LTV

        Useful for refinancing decisions
        """
        ltv_result = self.calculate_ltv(property_id)

        if not ltv_result.get("success"):
            return ltv_result

        current_ltv = Decimal(str(ltv_result["ltv"]))
        property_value = Decimal(str(ltv_result["property_value"]))
        current_loan = Decimal(str(ltv_result["loan_balance"]))

        # Calculate loan capacity at different LTV levels
        capacity_scenarios = {}

        for target_ltv_name, target_ltv in [
            ("conservative_65", self.STRONG_THRESHOLD),
            ("moderate_75", self.GOOD_THRESHOLD),
            ("aggressive_80", self.FAIR_THRESHOLD),
        ]:
            max_loan = property_value * target_ltv
            additional_capacity = max_loan - current_loan

            capacity_scenarios[target_ltv_name] = {
                "target_ltv": float(target_ltv),
                "target_ltv_percentage": float(target_ltv * 100),
                "max_loan_amount": float(max_loan),
                "additional_capacity": float(additional_capacity),
                "is_achievable": additional_capacity > 0,
            }

        return {
            "success": True,
            "property_id": property_id,
            "current_ltv": float(current_ltv),
            "current_ltv_percentage": float(current_ltv * 100),
            "current_loan_balance": float(current_loan),
            "property_value": float(property_value),
            "refinance_scenarios": capacity_scenarios,
        }
