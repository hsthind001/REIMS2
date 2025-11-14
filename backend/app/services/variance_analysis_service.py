"""
Variance Analysis Service

Analyzes variances between:
- Actual vs Budget
- Actual vs Forecast

Provides tolerance-based flagging and alert generation for significant variances.
"""
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime
import logging

from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.income_statement_data import IncomeStatementData
from app.models.balance_sheet_data import BalanceSheetData
from app.models.budget import Budget, BudgetStatus, Forecast
from app.models.committee_alert import CommitteeAlert, AlertType, AlertSeverity, AlertStatus, CommitteeType

logger = logging.getLogger(__name__)


class VarianceAnalysisService:
    """
    Variance Analysis Service

    Compares actual financial results against budgets and forecasts.
    Flags variances that exceed tolerance thresholds.
    """

    # Default tolerance thresholds
    DEFAULT_BUDGET_TOLERANCE_PCT = Decimal("10.0")     # 10%
    DEFAULT_FORECAST_TOLERANCE_PCT = Decimal("15.0")   # 15%

    # Variance severity thresholds
    WARNING_THRESHOLD_PCT = Decimal("10.0")    # 10% variance = warning
    CRITICAL_THRESHOLD_PCT = Decimal("25.0")   # 25% variance = critical
    URGENT_THRESHOLD_PCT = Decimal("50.0")     # 50% variance = urgent

    def __init__(self, db: Session):
        self.db = db

    def analyze_budget_variance(
        self,
        property_id: int,
        financial_period_id: int,
        budget_id: Optional[int] = None
    ) -> Dict:
        """
        Analyze variance between actual and budget

        Parameters:
        - property_id: Property ID
        - financial_period_id: Financial period ID
        - budget_id: Specific budget ID (optional, will find active budget if not provided)

        Returns:
        - Variance analysis by account
        - Summary totals
        - Flagged accounts exceeding tolerance
        """
        try:
            property = self.db.query(Property).filter(Property.id == property_id).first()
            if not property:
                return {"success": False, "error": "Property not found"}

            period = self.db.query(FinancialPeriod).filter(
                FinancialPeriod.id == financial_period_id
            ).first()
            if not period:
                return {"success": False, "error": "Financial period not found"}

            # Get budgets for this property and period
            budget_query = self.db.query(Budget).filter(
                Budget.property_id == property_id,
                Budget.financial_period_id == financial_period_id,
                Budget.status == BudgetStatus.ACTIVE
            )

            if budget_id:
                budgets = budget_query.filter(Budget.id == budget_id).all()
            else:
                budgets = budget_query.all()

            if not budgets:
                return {
                    "success": False,
                    "error": "No active budget found for this property and period"
                }

            # Get actual data
            actual_income = self.db.query(IncomeStatementData).filter(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.financial_period_id == financial_period_id
            ).all()

            actual_balance = self.db.query(BalanceSheetData).filter(
                BalanceSheetData.property_id == property_id,
                BalanceSheetData.financial_period_id == financial_period_id
            ).all()

            # Build actual amounts by account
            actual_by_account = {}

            for item in actual_income:
                if item.account_code:
                    actual_by_account[item.account_code] = {
                        "amount": Decimal(str(item.amount or 0)),
                        "account_name": item.account_name,
                        "source": "income_statement"
                    }

            for item in actual_balance:
                if item.account_code:
                    actual_by_account[item.account_code] = {
                        "amount": Decimal(str(item.amount or 0)),
                        "account_name": item.account_name,
                        "source": "balance_sheet"
                    }

            # Analyze variances
            variances = []
            flagged_accounts = []

            total_budget = Decimal("0")
            total_actual = Decimal("0")
            total_variance = Decimal("0")

            for budget in budgets:
                account_code = budget.account_code
                budgeted_amount = Decimal(str(budget.budgeted_amount))

                # Get actual amount
                actual_info = actual_by_account.get(account_code, {})
                actual_amount = actual_info.get("amount", Decimal("0"))
                account_name = actual_info.get("account_name") or budget.account_name

                # Calculate variance
                variance_amount = actual_amount - budgeted_amount
                variance_pct = (
                    (variance_amount / budgeted_amount * 100)
                    if budgeted_amount != 0
                    else Decimal("0")
                )

                # Determine if within tolerance
                tolerance_pct = budget.tolerance_percentage or self.DEFAULT_BUDGET_TOLERANCE_PCT
                tolerance_amount = budget.tolerance_amount

                within_tolerance = self._is_within_tolerance(
                    actual_amount=float(actual_amount),
                    budgeted_amount=float(budgeted_amount),
                    tolerance_pct=float(tolerance_pct),
                    tolerance_amount=float(tolerance_amount) if tolerance_amount else None
                )

                # Determine severity
                severity = self._determine_variance_severity(abs(variance_pct))

                variance_data = {
                    "budget_id": budget.id,
                    "account_code": account_code,
                    "account_name": account_name,
                    "account_category": budget.account_category,
                    "budgeted_amount": float(budgeted_amount),
                    "actual_amount": float(actual_amount),
                    "variance_amount": float(variance_amount),
                    "variance_percentage": float(variance_pct),
                    "within_tolerance": within_tolerance,
                    "tolerance_percentage": float(tolerance_pct),
                    "severity": severity,
                    "favorable": self._is_favorable_variance(
                        account_code,
                        float(variance_amount)
                    ),
                }

                variances.append(variance_data)

                # Track flagged accounts
                if not within_tolerance:
                    flagged_accounts.append(variance_data)

                    # Create alert for critical variances
                    if severity in ["CRITICAL", "URGENT"]:
                        self._create_variance_alert(
                            property_id=property_id,
                            financial_period_id=financial_period_id,
                            variance_data=variance_data,
                            variance_type="budget"
                        )

                # Accumulate totals
                total_budget += budgeted_amount
                total_actual += actual_amount
                total_variance += variance_amount

            # Calculate summary
            total_variance_pct = (
                (total_variance / total_budget * 100)
                if total_budget != 0
                else Decimal("0")
            )

            return {
                "success": True,
                "property_id": property_id,
                "property_name": property.property_name,
                "financial_period_id": financial_period_id,
                "period": {
                    "start_date": period.period_start_date.isoformat(),
                    "end_date": period.period_end_date.isoformat(),
                    "period_type": period.period_type,
                },
                "variance_type": "budget",
                "analysis_date": datetime.utcnow().isoformat(),
                "summary": {
                    "total_budgeted": float(total_budget),
                    "total_actual": float(total_actual),
                    "total_variance": float(total_variance),
                    "total_variance_percentage": float(total_variance_pct),
                    "accounts_analyzed": len(variances),
                    "flagged_accounts": len(flagged_accounts),
                    "within_tolerance": len(variances) - len(flagged_accounts),
                },
                "variances": variances,
                "flagged_accounts": flagged_accounts,
            }

        except Exception as e:
            logger.error(f"Budget variance analysis failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def analyze_forecast_variance(
        self,
        property_id: int,
        financial_period_id: int,
        forecast_id: Optional[int] = None
    ) -> Dict:
        """
        Analyze variance between actual and forecast

        Similar to budget variance but compares against forecast
        """
        try:
            property = self.db.query(Property).filter(Property.id == property_id).first()
            if not property:
                return {"success": False, "error": "Property not found"}

            period = self.db.query(FinancialPeriod).filter(
                FinancialPeriod.id == financial_period_id
            ).first()
            if not period:
                return {"success": False, "error": "Financial period not found"}

            # Get forecasts
            forecast_query = self.db.query(Forecast).filter(
                Forecast.property_id == property_id,
                Forecast.financial_period_id == financial_period_id,
                Forecast.status == BudgetStatus.ACTIVE
            )

            if forecast_id:
                forecasts = forecast_query.filter(Forecast.id == forecast_id).all()
            else:
                # Get most recent forecast
                forecasts = forecast_query.order_by(Forecast.forecast_date.desc()).all()

            if not forecasts:
                return {
                    "success": False,
                    "error": "No active forecast found for this property and period"
                }

            # Get actual data (same as budget variance)
            actual_income = self.db.query(IncomeStatementData).filter(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.financial_period_id == financial_period_id
            ).all()

            actual_balance = self.db.query(BalanceSheetData).filter(
                BalanceSheetData.property_id == property_id,
                BalanceSheetData.financial_period_id == financial_period_id
            ).all()

            # Build actual amounts by account
            actual_by_account = {}

            for item in actual_income:
                if item.account_code:
                    actual_by_account[item.account_code] = {
                        "amount": Decimal(str(item.amount or 0)),
                        "account_name": item.account_name,
                    }

            for item in actual_balance:
                if item.account_code:
                    actual_by_account[item.account_code] = {
                        "amount": Decimal(str(item.amount or 0)),
                        "account_name": item.account_name,
                    }

            # Analyze variances
            variances = []
            flagged_accounts = []

            total_forecast = Decimal("0")
            total_actual = Decimal("0")
            total_variance = Decimal("0")

            for forecast in forecasts:
                account_code = forecast.account_code
                forecasted_amount = Decimal(str(forecast.forecasted_amount))

                # Get actual amount
                actual_info = actual_by_account.get(account_code, {})
                actual_amount = actual_info.get("amount", Decimal("0"))
                account_name = actual_info.get("account_name") or forecast.account_name

                # Calculate variance
                variance_amount = actual_amount - forecasted_amount
                variance_pct = (
                    (variance_amount / forecasted_amount * 100)
                    if forecasted_amount != 0
                    else Decimal("0")
                )

                # Determine if within tolerance
                tolerance_pct = forecast.tolerance_percentage or self.DEFAULT_FORECAST_TOLERANCE_PCT
                tolerance_amount = forecast.tolerance_amount

                within_tolerance = self._is_within_tolerance(
                    actual_amount=float(actual_amount),
                    budgeted_amount=float(forecasted_amount),
                    tolerance_pct=float(tolerance_pct),
                    tolerance_amount=float(tolerance_amount) if tolerance_amount else None
                )

                # Determine severity
                severity = self._determine_variance_severity(abs(variance_pct))

                variance_data = {
                    "forecast_id": forecast.id,
                    "forecast_type": forecast.forecast_type,
                    "forecast_date": forecast.forecast_date.isoformat(),
                    "account_code": account_code,
                    "account_name": account_name,
                    "account_category": forecast.account_category,
                    "forecasted_amount": float(forecasted_amount),
                    "actual_amount": float(actual_amount),
                    "variance_amount": float(variance_amount),
                    "variance_percentage": float(variance_pct),
                    "within_tolerance": within_tolerance,
                    "tolerance_percentage": float(tolerance_pct),
                    "severity": severity,
                    "favorable": self._is_favorable_variance(
                        account_code,
                        float(variance_amount)
                    ),
                }

                variances.append(variance_data)

                # Track flagged accounts
                if not within_tolerance:
                    flagged_accounts.append(variance_data)

                    # Create alert for critical variances
                    if severity in ["CRITICAL", "URGENT"]:
                        self._create_variance_alert(
                            property_id=property_id,
                            financial_period_id=financial_period_id,
                            variance_data=variance_data,
                            variance_type="forecast"
                        )

                # Accumulate totals
                total_forecast += forecasted_amount
                total_actual += actual_amount
                total_variance += variance_amount

            # Calculate summary
            total_variance_pct = (
                (total_variance / total_forecast * 100)
                if total_forecast != 0
                else Decimal("0")
            )

            return {
                "success": True,
                "property_id": property_id,
                "property_name": property.property_name,
                "financial_period_id": financial_period_id,
                "period": {
                    "start_date": period.period_start_date.isoformat(),
                    "end_date": period.period_end_date.isoformat(),
                    "period_type": period.period_type,
                },
                "variance_type": "forecast",
                "analysis_date": datetime.utcnow().isoformat(),
                "summary": {
                    "total_forecasted": float(total_forecast),
                    "total_actual": float(total_actual),
                    "total_variance": float(total_variance),
                    "total_variance_percentage": float(total_variance_pct),
                    "accounts_analyzed": len(variances),
                    "flagged_accounts": len(flagged_accounts),
                    "within_tolerance": len(variances) - len(flagged_accounts),
                },
                "variances": variances,
                "flagged_accounts": flagged_accounts,
            }

        except Exception as e:
            logger.error(f"Forecast variance analysis failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_variance_report(
        self,
        property_id: int,
        financial_period_id: int,
        include_budget: bool = True,
        include_forecast: bool = True
    ) -> Dict:
        """
        Get comprehensive variance report including both budget and forecast

        Returns combined analysis of budget vs actual and forecast vs actual
        """
        result = {
            "success": True,
            "property_id": property_id,
            "financial_period_id": financial_period_id,
        }

        if include_budget:
            budget_variance = self.analyze_budget_variance(property_id, financial_period_id)
            result["budget_variance"] = budget_variance

        if include_forecast:
            forecast_variance = self.analyze_forecast_variance(property_id, financial_period_id)
            result["forecast_variance"] = forecast_variance

        return result

    def get_variance_trend(
        self,
        property_id: int,
        lookback_periods: int = 6,
        variance_type: str = "budget"
    ) -> Dict:
        """
        Get variance trend over time

        Shows how variances are trending across multiple periods
        """
        try:
            property = self.db.query(Property).filter(Property.id == property_id).first()
            if not property:
                return {"success": False, "error": "Property not found"}

            # Get recent periods
            periods = self.db.query(FinancialPeriod).filter(
                FinancialPeriod.property_id == property_id
            ).order_by(FinancialPeriod.period_end_date.desc()).limit(lookback_periods).all()

            trend_data = []

            for period in reversed(periods):
                if variance_type == "budget":
                    analysis = self.analyze_budget_variance(property_id, period.id)
                else:
                    analysis = self.analyze_forecast_variance(property_id, period.id)

                if analysis.get("success"):
                    trend_data.append({
                        "period_id": period.id,
                        "period_date": period.period_end_date.isoformat(),
                        "total_variance_percentage": analysis["summary"]["total_variance_percentage"],
                        "flagged_accounts": analysis["summary"]["flagged_accounts"],
                    })

            return {
                "success": True,
                "property_id": property_id,
                "property_name": property.property_name,
                "variance_type": variance_type,
                "lookback_periods": lookback_periods,
                "trend_data": trend_data,
            }

        except Exception as e:
            logger.error(f"Variance trend analysis failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def _is_within_tolerance(
        self,
        actual_amount: float,
        budgeted_amount: float,
        tolerance_pct: float,
        tolerance_amount: Optional[float] = None
    ) -> bool:
        """
        Check if actual is within tolerance of budget/forecast
        """
        variance = abs(actual_amount - budgeted_amount)

        # Check percentage tolerance
        if tolerance_pct:
            max_variance_pct = abs(budgeted_amount) * (tolerance_pct / 100)
            if variance <= max_variance_pct:
                return True

        # Check absolute tolerance
        if tolerance_amount:
            if variance <= tolerance_amount:
                return True

        return False

    def _determine_variance_severity(self, abs_variance_pct: Decimal) -> str:
        """
        Determine severity based on variance percentage
        """
        if abs_variance_pct >= self.URGENT_THRESHOLD_PCT:
            return "URGENT"
        elif abs_variance_pct >= self.CRITICAL_THRESHOLD_PCT:
            return "CRITICAL"
        elif abs_variance_pct >= self.WARNING_THRESHOLD_PCT:
            return "WARNING"
        else:
            return "INFO"

    def _is_favorable_variance(self, account_code: str, variance_amount: float) -> bool:
        """
        Determine if variance is favorable or unfavorable

        Revenue accounts (4xxxx): Positive variance = favorable
        Expense accounts (5xxxx, 6xxxx): Negative variance = favorable
        """
        if account_code.startswith("4"):
            # Revenue: actual > budget is favorable
            return variance_amount > 0
        elif account_code.startswith("5") or account_code.startswith("6"):
            # Expenses: actual < budget is favorable
            return variance_amount < 0
        else:
            # For other accounts, positive variance is generally favorable
            return variance_amount > 0

    def _create_variance_alert(
        self,
        property_id: int,
        financial_period_id: int,
        variance_data: Dict,
        variance_type: str
    ) -> Optional[CommitteeAlert]:
        """
        Create alert for significant variance
        """
        try:
            # Check if alert already exists
            existing_alert = self.db.query(CommitteeAlert).filter(
                CommitteeAlert.property_id == property_id,
                CommitteeAlert.financial_period_id == financial_period_id,
                CommitteeAlert.alert_type == AlertType.VARIANCE_BREACH,
                CommitteeAlert.status == AlertStatus.ACTIVE,
                CommitteeAlert.related_metric == variance_data["account_code"]
            ).first()

            if existing_alert:
                return None  # Don't create duplicate

            severity_map = {
                "URGENT": AlertSeverity.URGENT,
                "CRITICAL": AlertSeverity.CRITICAL,
                "WARNING": AlertSeverity.WARNING,
                "INFO": AlertSeverity.INFO,
            }

            severity = severity_map.get(variance_data["severity"], AlertSeverity.WARNING)

            # Build description
            variance_direction = "favorable" if variance_data["favorable"] else "unfavorable"

            if variance_type == "budget":
                comparison = "budget"
                expected_amount = variance_data["budgeted_amount"]
            else:
                comparison = "forecast"
                expected_amount = variance_data["forecasted_amount"]

            description = (
                f"Significant {variance_direction} variance detected in {variance_data['account_name']} "
                f"({variance_data['account_code']}).\n\n"
                f"{comparison.title()}: ${expected_amount:,.2f}\n"
                f"Actual: ${variance_data['actual_amount']:,.2f}\n"
                f"Variance: ${variance_data['variance_amount']:,.2f} "
                f"({variance_data['variance_percentage']:+.1f}%)\n"
                f"Tolerance: ±{variance_data['tolerance_percentage']:.1f}%\n\n"
                f"This variance exceeds acceptable tolerance levels and requires review."
            )

            alert = CommitteeAlert(
                property_id=property_id,
                financial_period_id=financial_period_id,
                alert_type=AlertType.VARIANCE_BREACH,
                severity=severity,
                status=AlertStatus.ACTIVE,
                title=f"Variance Alert: {variance_data['account_name']} ({variance_data['variance_percentage']:+.1f}%)",
                description=description,
                threshold_value=Decimal(str(variance_data['tolerance_percentage'])),
                actual_value=Decimal(str(abs(variance_data['variance_percentage']))),
                threshold_unit="percentage",
                assigned_committee=CommitteeType.FINANCE_SUBCOMMITTEE,
                requires_approval=severity in [AlertSeverity.CRITICAL, AlertSeverity.URGENT],
                related_metric=variance_data["account_code"],
                br_id="BR-005",
                metadata={
                    "variance_type": variance_type,
                    "variance_data": variance_data,
                }
            )

            self.db.add(alert)
            self.db.commit()
            self.db.refresh(alert)

            logger.info(f"Variance alert created: {alert.id} for property {property_id}, account {variance_data['account_code']}")
            return alert

        except Exception as e:
            logger.error(f"Failed to create variance alert: {str(e)}")
            self.db.rollback()
            return None
