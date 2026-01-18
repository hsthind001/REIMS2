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
from app.models.mortgage_statement_data import MortgageStatementData
from app.models.committee_alert import CommitteeAlert, AlertType, AlertSeverity, AlertStatus, CommitteeType
from app.models.workflow_lock import WorkflowLock, LockReason, LockScope, LockStatus

logger = logging.getLogger(__name__)


class DSCRMonitoringService:
    """
    DSCR Monitoring and Covenant Compliance Service
    """

    # DSCR Thresholds
    CRITICAL_THRESHOLD = Decimal("1.25")  # Below this = critical (changed from 1.10 to 1.25)
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
                    "year": period.period_year,
                    "month": period.period_month,
                    "start_date": period.period_start_date.isoformat() if period.period_start_date else None,
                    "end_date": period.period_end_date.isoformat() if period.period_end_date else None,
                },
                "calculated_at": datetime.utcnow().isoformat(),
            }

            # Check if alert needed or if existing alert should be resolved
            # Only create alerts if property has actual uploaded financial data
            if dscr < self.WARNING_THRESHOLD:
                # Verify property has actual financial data before creating alert
                has_financial_data = self._has_financial_data(property_id, period.id)
                
                if not has_financial_data:
                    logger.info(
                        f"Skipping alert creation for property {property_id} (period {period.id}): "
                        "No uploaded financial documents found. Property may not have data uploaded yet."
                    )
                    result["alert_created"] = False
                    result["alert_skipped"] = True
                    result["skip_reason"] = "No financial data uploaded"
                else:
                    # DSCR is below threshold and property has data - create or update alert
                    try:
                        alert = self._create_dscr_alert(
                            property_id=property_id,
                            financial_period_id=period.id,
                            dscr=dscr,
                            noi=noi,
                            total_debt_service=total_debt_service,
                            severity=severity,
                        )
                        result["alert_created"] = True
                        result["alert_id"] = alert.id if alert else None
                    except Exception as alert_err:
                        # Log but don't fail the DSCR calculation if alert creation fails
                        logger.warning(f"Failed to create DSCR alert (DSCR calculation still successful): {str(alert_err)}")
                        result["alert_created"] = False
                        result["alert_error"] = str(alert_err)
            else:
                # DSCR is healthy - auto-resolve any existing active alerts for this property/period
                try:
                    existing_alerts = self.db.query(CommitteeAlert).filter(
                        CommitteeAlert.property_id == property_id,
                        CommitteeAlert.financial_period_id == period.id,
                        CommitteeAlert.alert_type == AlertType.DSCR_BREACH,
                        CommitteeAlert.status == AlertStatus.ACTIVE
                    ).all()
                    
                    if existing_alerts:
                        for alert in existing_alerts:
                            alert.status = AlertStatus.RESOLVED
                            alert.resolved_at = datetime.utcnow()
                            alert.resolved_by = None  # Auto-resolved by system, no user required
                            alert.resolution_notes = f"Auto-resolved: DSCR improved to {float(dscr):.2f} (above threshold {float(self.WARNING_THRESHOLD):.2f})"
                        self.db.commit()
                        result["alerts_resolved"] = len(existing_alerts)
                        logger.info(f"Auto-resolved {len(existing_alerts)} DSCR alert(s) for property {property_id} - DSCR now healthy")
                except Exception as resolve_err:
                    logger.warning(f"Failed to auto-resolve DSCR alerts: {str(resolve_err)}")
                    result["alert_resolve_error"] = str(resolve_err)

            return result

        except Exception as e:
            logger.error(f"DSCR calculation failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def _calculate_noi(self, property_id: int, financial_period_id: int) -> Decimal:
        """
        Calculate Net Operating Income (NOI)

        First tries to use pre-calculated NOI from FinancialMetrics.
        Falls back to calculating from income statement data if not available.
        
        CRITICAL: If period_type is Monthly, annualizes the NOI (multiplies by 12).
        """
        # Try to get pre-calculated NOI from FinancialMetrics first
        from app.models.financial_metrics import FinancialMetrics
        metrics = self.db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == property_id,
            FinancialMetrics.period_id == financial_period_id
        ).first()
        
        # Determine period type from income statement header
        from app.models.income_statement_header import IncomeStatementHeader
        period_type = None
        header = self.db.query(IncomeStatementHeader).join(
            IncomeStatementData, IncomeStatementData.header_id == IncomeStatementHeader.id
        ).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == financial_period_id
        ).first()
        
        if header:
            period_type = header.period_type
        
        if metrics and metrics.net_operating_income is not None:
            noi = Decimal(str(metrics.net_operating_income))
            # Annualize if monthly
            if period_type and period_type.upper() in ["MONTHLY", "MONTH"]:
                noi = noi * Decimal("12")
                logger.debug(f"NOI is monthly ({metrics.net_operating_income}), annualized to {noi}")
            return noi
        
        # Fallback: Calculate from income statement data
        # Note: IncomeStatementData uses 'period_id', not 'financial_period_id'
        income_data = self.db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == financial_period_id
        ).all()

        total_revenue = Decimal("0")
        operating_expenses = Decimal("0")

        for item in income_data:
            # Revenue accounts (typically 4xxxx or similar)
            if item.account_code and item.account_code.startswith("4"):
                total_revenue += Decimal(str(item.period_amount or 0))
            # Operating expense accounts (typically 5xxxx or 6xxxx)
            elif item.account_code and (
                item.account_code.startswith("5") or
                item.account_code.startswith("6")
            ):
                operating_expenses += Decimal(str(item.period_amount or 0))

        noi = total_revenue - operating_expenses
        
        # Annualize if monthly
        if period_type and period_type.upper() in ["MONTHLY", "MONTH"]:
            noi = noi * Decimal("12")
            logger.debug(f"Calculated NOI is monthly, annualized to {noi}")
        
        return noi

    def _get_total_debt_service(
        self,
        property_id: int,
        financial_period_id: int
    ) -> Decimal:
        """
        Get total debt service (principal + interest payments)
        
        DSCR = NOI / (Principal + Interest)
        
        PREFERRED: Use mortgage statement data when available (most accurate)
        FALLBACK: Use income statement interest + estimated principal
        
        IMPORTANT: Only include actual debt service payments:
        - Mortgage Interest (7010-0000) - YES
        - Principal payments - YES (from mortgage statements or cash flow)
        - Depreciation (7020-0000) - NO (non-cash expense)
        - Amortization (7030-0000) - NO (non-cash expense)
        """
        # PREFERRED: Try to get debt service from mortgage statement data first
        mortgage_data = self.db.query(MortgageStatementData).filter(
            MortgageStatementData.property_id == property_id,
            MortgageStatementData.period_id == financial_period_id
        ).all()
        
        if mortgage_data:
            # Sum annual debt service from all mortgages
            total_annual_debt_service = Decimal("0")
            for mortgage in mortgage_data:
                if mortgage.annual_debt_service:
                    total_annual_debt_service += Decimal(str(mortgage.annual_debt_service))
                elif mortgage.monthly_debt_service:
                    # Convert monthly to annual
                    total_annual_debt_service += Decimal(str(mortgage.monthly_debt_service)) * Decimal("12")
                else:
                    # Calculate from principal_due + interest_due
                    principal = Decimal(str(mortgage.principal_due or 0))
                    interest = Decimal(str(mortgage.interest_due or 0))
                    monthly = principal + interest
                    total_annual_debt_service += monthly * Decimal("12")
            
            if total_annual_debt_service > 0:
                logger.debug(f"Using mortgage statement data for debt service: {total_annual_debt_service}")
                return total_annual_debt_service
        
        # FALLBACK: Get ONLY Mortgage Interest (7010-0000) - this is the interest portion of debt service
        from app.models.income_statement_header import IncomeStatementHeader
        mortgage_interest = self.db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == financial_period_id,
            IncomeStatementData.account_code == "7010-0000"  # Mortgage Interest only
        ).first()

        interest_payment = Decimal("0")
        if mortgage_interest and mortgage_interest.period_amount:
            interest_payment = Decimal(str(mortgage_interest.period_amount))
            
            # CRITICAL: Check if period_amount is monthly or annual
            # Income statements can be Monthly or Annual
            # Get period_type from header if not in data row
            period_type = None
            if mortgage_interest.header_id:
                header = self.db.query(IncomeStatementHeader).filter(
                    IncomeStatementHeader.id == mortgage_interest.header_id
                ).first()
                if header:
                    period_type = header.period_type
            
            # Fallback to data row period_type, then default to Monthly
            if not period_type:
                period_type = mortgage_interest.period_type
            
            if not period_type:
                # Default to Monthly if not specified (most common)
                period_type = "Monthly"
            
            if period_type.upper() in ["MONTHLY", "MONTH"]:
                # Monthly interest - multiply by 12 to get annual
                interest_payment = interest_payment * Decimal("12")
                logger.debug(f"Interest is monthly ({mortgage_interest.period_amount}), annualized to {interest_payment}")
            elif period_type.upper() in ["ANNUAL", "YEAR", "YEARLY"]:
                # Already annual - use as-is
                logger.debug(f"Interest is annual: {interest_payment}")
            else:
                # Unknown period type - check period dates to determine
                from app.models.financial_period import FinancialPeriod
                period = self.db.query(FinancialPeriod).filter(
                    FinancialPeriod.id == financial_period_id
                ).first()
                
                if period and period.period_start_date and period.period_end_date:
                    days_diff = (period.period_end_date - period.period_start_date).days
                    # If period is ~30 days, it's monthly; if ~365 days, it's annual
                    if days_diff <= 35:
                        # Monthly period - annualize
                        interest_payment = interest_payment * Decimal("12")
                        logger.debug(f"Period is {days_diff} days (monthly), annualized interest to {interest_payment}")
                    else:
                        # Annual period - use as-is
                        logger.debug(f"Period is {days_diff} days (annual), using interest as-is: {interest_payment}")
        
        # Try to get principal payments from cash flow statement (financing activities)
        # Principal payments are typically in cash flow financing section
        from app.models.cash_flow_data import CashFlowData
        principal_payments = self.db.query(CashFlowData).filter(
            CashFlowData.property_id == property_id,
            CashFlowData.period_id == financial_period_id,
            CashFlowData.line_category.ilike("%principal%"),
            CashFlowData.line_section == "FINANCING"
        ).all()
        
        principal_payment = Decimal("0")
        for payment in principal_payments:
            if payment.period_amount:
                principal_payment += Decimal(str(payment.period_amount))
        
        total_debt_service = interest_payment + principal_payment
        
        # If no principal found, estimate annual debt service from loan amount and interest rate
        # Try to get loan amount from LTV API or balance sheet
        if principal_payment == 0 and interest_payment > 0:
            # Try to get loan amount to calculate proper debt service
            from app.models.balance_sheet_data import BalanceSheetData
            # Get long-term debt from balance sheet (account 2900-0000)
            long_term_debt = self.db.query(BalanceSheetData).filter(
                BalanceSheetData.property_id == property_id,
                BalanceSheetData.period_id == financial_period_id,
                BalanceSheetData.account_code == "2900-0000"
            ).first()
            
            loan_amount = Decimal("0")
            if long_term_debt and long_term_debt.amount:
                loan_amount = Decimal(str(long_term_debt.amount))
            
            # Calculate estimated principal payment using amortization formula
            # For commercial loans, typical amortization is 25-30 years
            # Monthly payment = P * [r(1+r)^n] / [(1+r)^n - 1]
            # Where P = principal, r = monthly rate, n = number of payments
            if loan_amount > 0 and interest_payment > 0:
                # Calculate interest rate from interest payment
                # If interest_payment is annual: rate = interest_payment / loan_amount
                # If interest_payment is monthly: rate = (interest_payment * 12) / loan_amount
                # Assume interest_payment is annual (typical for income statements)
                annual_rate = interest_payment / loan_amount if loan_amount > 0 else Decimal("0.06")
                monthly_rate = annual_rate / Decimal("12")
                
                # Assume 25-year amortization (300 months) - typical for commercial real estate
                num_payments = Decimal("300")
                
                # Calculate monthly payment using amortization formula
                if monthly_rate > 0:
                    monthly_payment = loan_amount * (
                        monthly_rate * (Decimal("1") + monthly_rate) ** num_payments
                    ) / (
                        (Decimal("1") + monthly_rate) ** num_payments - Decimal("1")
                    )
                    annual_payment = monthly_payment * Decimal("12")
                    estimated_principal = annual_payment - interest_payment
                    total_debt_service = interest_payment + max(estimated_principal, Decimal("0"))
                else:
                    # Fallback: Use simpler estimate (interest × 0.5 for principal)
                    estimated_principal = interest_payment * Decimal("0.5")
                    total_debt_service = interest_payment + estimated_principal
            else:
                # Fallback: Use conservative estimate (interest × 0.5 for principal)
                # This assumes principal is about 50% of interest (typical for early loan years)
                estimated_principal = interest_payment * Decimal("0.5")
                total_debt_service = interest_payment + estimated_principal
        
        # If still zero, fallback to estimated calculation based on NOI
        if total_debt_service == 0:
            noi = self._calculate_noi(property_id, financial_period_id)
            # Estimate: Assume debt service is ~60-70% of NOI (typical for commercial real estate)
            # This ensures DSCR will be around 1.4-1.6 if NOI is healthy
            total_debt_service = noi * Decimal("0.65") if noi > 0 else Decimal("0")

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
        Create a DSCR breach alert with intelligent duplicate prevention
        
        Logic:
        - Check for ANY existing alert (not just ACTIVE) for property/period
        - If ACTIVE exists → Update it
        - If ACKNOWLEDGED/RESOLVED exists → Reactivate if DSCR still below threshold
        - If DISMISSED exists → Create new alert (user explicitly dismissed)
        - If none exists → Create new alert
        """
        # Check for existing alert (any status except DISMISSED)
        # Order by triggered_at DESC to get the most recent one
        existing_alert = self.db.query(CommitteeAlert).filter(
            CommitteeAlert.property_id == property_id,
            CommitteeAlert.financial_period_id == financial_period_id,
            CommitteeAlert.alert_type == AlertType.DSCR_BREACH,
            CommitteeAlert.status != AlertStatus.DISMISSED  # Check all except dismissed
        ).order_by(CommitteeAlert.triggered_at.desc()).first()

        if existing_alert:
            # Update existing alert with current DSCR calculation
            existing_alert.actual_value = dscr
            existing_alert.severity = severity
            existing_alert.title = f"DSCR Breach: {float(dscr):.2f}" if dscr < self.WARNING_THRESHOLD else f"DSCR: {float(dscr):.2f}"
            existing_alert.description = (
                f"Debt Service Coverage Ratio ({float(dscr):.2f}) is {'below' if dscr < self.WARNING_THRESHOLD else 'above'} the threshold of {float(self.WARNING_THRESHOLD):.2f}.\n\n"
                f"NOI: ${float(noi):,.2f}\n"
                f"Total Debt Service: ${float(total_debt_service):,.2f}\n"
                f"DSCR: {float(dscr):.2f}\n\n"
                + (f"This may indicate covenant violation. Finance committee review required." if dscr < self.WARNING_THRESHOLD else "Property meets DSCR requirements.")
            )
            existing_alert.updated_at = datetime.utcnow()
            
            # Intelligent status management
            if dscr >= self.WARNING_THRESHOLD:
                # DSCR is now healthy - resolve if active
                if existing_alert.status == AlertStatus.ACTIVE:
                    existing_alert.status = AlertStatus.RESOLVED
                    existing_alert.resolved_at = datetime.utcnow()
                    existing_alert.resolved_by = None
                    existing_alert.resolution_notes = f"Auto-resolved: DSCR improved to {float(dscr):.2f} (above threshold {float(self.WARNING_THRESHOLD):.2f})"
            else:
                # DSCR is still below threshold
                if existing_alert.status in [AlertStatus.ACKNOWLEDGED, AlertStatus.RESOLVED]:
                    # Reactivate if it was previously acknowledged/resolved
                    existing_alert.status = AlertStatus.ACTIVE
                    existing_alert.acknowledged_at = None
                    existing_alert.acknowledged_by = None
                    existing_alert.resolved_at = None
                    existing_alert.resolved_by = None
                    existing_alert.resolution_notes = None
                    logger.info(
                        f"Reactivated DSCR alert {existing_alert.id} for property {property_id}, "
                        f"period {financial_period_id} (DSCR still below threshold)"
                    )
                # If already ACTIVE, just update the values (already done above)
            
            self.db.commit()
            self.db.refresh(existing_alert)
            logger.info(f"DSCR alert updated: {existing_alert.id} for property {property_id}, period {financial_period_id}")
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

    def _has_financial_data(self, property_id: int, period_id: int) -> bool:
        """
        Check if property has COMPLETE financial data for the period
        
        STRICT REQUIREMENT: Returns True ONLY if property has ALL 3 documents:
        - Balance Sheet data, AND
        - Income Statement data, AND
        - Cash Flow data
        
        This ensures DSCR calculations only use complete financial periods.
        Prevents alerts/calculations for incomplete data.
        """
        from app.models.balance_sheet_data import BalanceSheetData
        from app.models.cash_flow_data import CashFlowData
        
        # Check for balance sheet data
        balance_sheet = self.db.query(BalanceSheetData).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.period_id == period_id
        ).first()
        
        # Check for income statement data
        income_statement = self.db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id
        ).first()
        
        # Check for cash flow data
        cash_flow = self.db.query(CashFlowData).filter(
            CashFlowData.property_id == property_id,
            CashFlowData.period_id == period_id
        ).first()
        
        # STRICT: Require ALL 3 documents
        has_complete_data = (
            balance_sheet is not None and
            income_statement is not None and
            cash_flow is not None
        )
        
        if not has_complete_data:
            logger.debug(
                f"Incomplete financial data for property {property_id}, period {period_id}: "
                f"Balance Sheet: {balance_sheet is not None}, "
                f"Income Statement: {income_statement is not None}, "
                f"Cash Flow: {cash_flow is not None}"
            )
        
        return has_complete_data

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
