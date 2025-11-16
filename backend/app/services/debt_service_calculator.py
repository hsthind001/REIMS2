"""
Debt Service Calculator Service

Calculates debt service metrics from financial statement data:
- Extracts interest expense from Income Statement
- Extracts principal payments from Cash Flow Statement
- Calculates annual debt service (interest + principal)
- Calculates DSCR (NOI / annual debt service)
- Updates financial_metrics table with calculated values
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from app.models.financial_metrics import FinancialMetrics
from app.models.financial_period import FinancialPeriod
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData

logger = logging.getLogger(__name__)


class DebtServiceCalculator:
    """Calculate debt service metrics from financial statements"""

    # Keywords to identify interest expense in income statement
    INTEREST_KEYWORDS = [
        'interest expense',
        'mortgage interest',
        'loan interest',
        'debt interest',
        'interest - mortgage',
        'interest - loan'
    ]

    # Keywords to identify principal payments in cash flow
    PRINCIPAL_KEYWORDS = [
        'principal payment',
        'principal repayment',
        'mortgage principal',
        'loan principal',
        'debt principal',
        'amortization'
    ]

    # Account codes that typically represent interest expense
    INTEREST_ACCOUNT_CODES = [
        '7010-0000',  # Interest Expense
        '7010',  # Interest Expense variations
    ]

    def __init__(self, db: Session):
        self.db = db

    def calculate_for_period(
        self,
        property_id: int,
        period_id: int
    ) -> Dict[str, Any]:
        """
        Calculate debt service for a specific property and period

        Args:
            property_id: Property ID
            period_id: Financial Period ID

        Returns:
            Dictionary with calculated debt service metrics
        """
        try:
            # Get the financial period
            period = self.db.query(FinancialPeriod).filter(
                FinancialPeriod.id == period_id,
                FinancialPeriod.property_id == property_id
            ).first()

            if not period:
                raise ValueError(f"Financial period {period_id} not found for property {property_id}")

            # Extract interest expense from income statement
            annual_interest = self._extract_interest_expense(property_id, period)

            # Extract principal payments from cash flow
            annual_principal = self._extract_principal_payments(property_id, period)

            # Calculate total annual debt service
            annual_debt_service = (annual_interest or 0) + (annual_principal or 0)
            monthly_debt_service = annual_debt_service / 12 if annual_debt_service else None

            # Get NOI from financial metrics
            metrics = self.db.query(FinancialMetrics).filter(
                FinancialMetrics.property_id == property_id,
                FinancialMetrics.period_id == period_id
            ).first()

            noi = float(metrics.net_operating_income) if metrics and metrics.net_operating_income else None

            # Calculate DSCR
            dscr = None
            dscr_status = None
            if noi and annual_debt_service and annual_debt_service > 0:
                dscr = noi / annual_debt_service

                # Determine DSCR status
                if dscr >= 1.35:
                    dscr_status = 'good'
                elif dscr >= 1.25:
                    dscr_status = 'warning'
                else:
                    dscr_status = 'critical'

            result = {
                'property_id': property_id,
                'period_id': period_id,
                'annual_interest_expense': annual_interest,
                'annual_principal_payment': annual_principal,
                'annual_debt_service': annual_debt_service if annual_debt_service > 0 else None,
                'monthly_debt_service': monthly_debt_service,
                'dscr': round(dscr, 4) if dscr else None,
                'dscr_status': dscr_status,
                'debt_calculation_method': self._get_calculation_method(annual_interest, annual_principal),
                'debt_service_calculated_at': datetime.now()
            }

            logger.info(
                f"Calculated debt service for property {property_id}, period {period_id}: "
                f"Interest=${annual_interest}, Principal=${annual_principal}, "
                f"Total=${annual_debt_service}, DSCR={dscr}"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to calculate debt service: {str(e)}")
            raise

    def _extract_interest_expense(
        self,
        property_id: int,
        period: FinancialPeriod
    ) -> Optional[float]:
        """
        Extract total interest expense from income statement data

        Looks for accounts with keywords like "interest expense", "mortgage interest"
        or specific account codes for interest.
        """
        interest_accounts = self.db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period.id
        ).all()

        total_interest = 0.0
        found_accounts = []

        for account in interest_accounts:
            account_name = account.account_name.lower() if account.account_name else ""
            account_code = account.account_code or ""

            # Check if this is an interest expense account
            is_interest = False

            # Check by keyword
            if any(keyword in account_name for keyword in self.INTEREST_KEYWORDS):
                is_interest = True

            # Check by account code
            if any(account_code.startswith(code) for code in self.INTEREST_ACCOUNT_CODES):
                is_interest = True

            if is_interest and account.period_amount:
                amount = float(account.period_amount)
                # Interest expense is typically negative in income statement, so take absolute value
                total_interest += abs(amount)
                found_accounts.append(f"{account.account_name} ({account_code}): ${abs(amount):,.2f}")

        if found_accounts:
            logger.info(f"Found interest expense accounts: {', '.join(found_accounts)}")

        # All financial periods are monthly, so annualize the data
        if total_interest > 0:
            total_interest *= 12
            logger.info(f"Annualized monthly interest: ${total_interest:,.2f}")

        return total_interest if total_interest > 0 else None

    def _extract_principal_payments(
        self,
        property_id: int,
        period: FinancialPeriod
    ) -> Optional[float]:
        """
        Extract total principal payments from cash flow data

        Looks for financing activities with keywords like "principal payment"
        or loan/mortgage payments classified as principal.
        """
        cash_flow_accounts = self.db.query(CashFlowData).filter(
            CashFlowData.property_id == property_id,
            CashFlowData.period_id == period.id,
            CashFlowData.cash_flow_category == 'financing'  # Principal is in financing activities
        ).all()

        total_principal = 0.0
        found_accounts = []

        for account in cash_flow_accounts:
            account_name = account.account_name.lower() if account.account_name else ""
            account_code = account.account_code or ""

            # Check if this is a principal payment account
            is_principal = False

            # Check by keyword
            if any(keyword in account_name for keyword in self.PRINCIPAL_KEYWORDS):
                is_principal = True

            # Also check for mortgage/loan payments that are NOT interest
            # (they're likely principal)
            if ('mortgage' in account_name or 'loan' in account_name) and \
               not any(kw in account_name for kw in ['interest', 'expense']):
                # Only if it's a payment (negative value in cash flow)
                if account.period_amount and float(account.period_amount) < 0:
                    is_principal = True

            if is_principal and account.period_amount:
                amount = float(account.period_amount)
                # Principal payments are negative in cash flow (cash outflow), so take absolute value
                total_principal += abs(amount)
                found_accounts.append(f"{account.account_name} ({account_code}): ${abs(amount):,.2f}")

        if found_accounts:
            logger.info(f"Found principal payment accounts: {', '.join(found_accounts)}")

        # All financial periods are monthly, so annualize the data
        if total_principal > 0:
            total_principal *= 12
            logger.info(f"Annualized monthly principal: ${total_principal:,.2f}")

        return total_principal if total_principal > 0 else None

    def _get_calculation_method(
        self,
        interest: Optional[float],
        principal: Optional[float]
    ) -> str:
        """
        Determine how debt service was calculated
        """
        if interest and principal:
            return 'income_statement_and_cash_flow'
        elif interest:
            return 'income_statement_only'
        elif principal:
            return 'cash_flow_only'
        else:
            return 'no_data'

    def update_financial_metrics(
        self,
        property_id: int,
        period_id: int
    ) -> bool:
        """
        Calculate debt service and update financial_metrics table

        Args:
            property_id: Property ID
            period_id: Financial Period ID

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            # Calculate debt service
            debt_service_data = self.calculate_for_period(property_id, period_id)

            # Get or create financial metrics record
            metrics = self.db.query(FinancialMetrics).filter(
                FinancialMetrics.property_id == property_id,
                FinancialMetrics.period_id == period_id
            ).first()

            if not metrics:
                logger.warning(
                    f"No financial metrics found for property {property_id}, "
                    f"period {period_id}. Skipping debt service update."
                )
                return False

            # Update debt service fields
            metrics.annual_interest_expense = debt_service_data['annual_interest_expense']
            metrics.annual_principal_payment = debt_service_data['annual_principal_payment']
            metrics.annual_debt_service = debt_service_data['annual_debt_service']
            metrics.monthly_debt_service = debt_service_data['monthly_debt_service']
            metrics.dscr = debt_service_data['dscr']
            metrics.dscr_status = debt_service_data['dscr_status']
            metrics.debt_calculation_method = debt_service_data['debt_calculation_method']
            metrics.debt_service_calculated_at = debt_service_data['debt_service_calculated_at']

            self.db.commit()

            logger.info(
                f"Updated financial metrics for property {property_id}, period {period_id} "
                f"with DSCR={debt_service_data['dscr']}"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to update financial metrics: {str(e)}")
            self.db.rollback()
            return False

    def calculate_all_properties(self) -> Dict[str, Any]:
        """
        Calculate debt service for all properties and periods

        Returns:
            Summary of calculations performed
        """
        summary = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'properties': []
        }

        # Get all financial metrics records
        all_metrics = self.db.query(FinancialMetrics).all()

        for metrics in all_metrics:
            summary['total_processed'] += 1

            try:
                success = self.update_financial_metrics(
                    metrics.property_id,
                    metrics.period_id
                )

                if success:
                    summary['successful'] += 1
                    summary['properties'].append({
                        'property_id': metrics.property_id,
                        'period_id': metrics.period_id,
                        'status': 'success'
                    })
                else:
                    summary['failed'] += 1
                    summary['properties'].append({
                        'property_id': metrics.property_id,
                        'period_id': metrics.period_id,
                        'status': 'no_data'
                    })

            except Exception as e:
                summary['failed'] += 1
                summary['properties'].append({
                    'property_id': metrics.property_id,
                    'period_id': metrics.period_id,
                    'status': 'error',
                    'error': str(e)
                })

        logger.info(
            f"Debt service calculation complete: {summary['successful']}/{summary['total_processed']} successful"
        )

        return summary
