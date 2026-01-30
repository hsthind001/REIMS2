"""
Covenant Compliance Service - Phase 7 of Forensic Audit Framework

Monitors lender covenant compliance with automated alerts:
- DSCR (Debt Service Coverage Ratio) - Rule A-7.1
- LTV (Loan-to-Value Ratio) - Rule A-7.2
- Interest Coverage Ratio - Rule A-7.3
- Liquidity Ratios - Rule A-7.4
- Cash Burn Rate Analysis - Rule A-7.5
"""

from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select

from app.models import SystemConfig
from app.services.rules.covenant_resolver import (
    resolve_covenant_threshold_async,
    get_covenant_threshold_async,
)


class CovenantComplianceService:
    """
    Monitors lender covenant compliance for commercial real estate loans.

    Covenant breaches trigger critical alerts to Finance/Risk committees.
    """

    # DSCR thresholds (industry standard for CRE)
    # NOTE: These class-level constants act as sane defaults.
    #       Actual runtime thresholds can be overridden from the
    #       `system_config` table via the helper methods below.
    DSCR_COVENANT_MINIMUM = Decimal("1.25")  # Typical lender requirement
    DSCR_STRONG = Decimal("1.50")  # Strong performance
    DSCR_ADEQUATE = Decimal("1.25")  # Minimum covenant
    DSCR_WARNING = Decimal("1.15")  # Warning zone
    DSCR_CRITICAL = Decimal("1.00")  # Break-even

    # LTV thresholds
    LTV_COVENANT_MAXIMUM = Decimal("75.0")  # Typical lender limit (percent)
    LTV_CONSERVATIVE = Decimal("65.0")  # Conservative
    LTV_WARNING = Decimal("70.0")  # Approaching covenant
    LTV_CRITICAL = Decimal("75.0")  # At covenant limit

    # Interest Coverage Ratio thresholds
    ICR_MINIMUM = Decimal("2.0")  # Typical covenant
    ICR_STRONG = Decimal("3.0")  # Strong coverage

    # Liquidity thresholds
    CURRENT_RATIO_MINIMUM = Decimal("1.5")
    QUICK_RATIO_MINIMUM = Decimal("1.0")

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_config_threshold(
        self,
        key: str,
        default: Decimal,
    ) -> Decimal:
        """
        Fetch a numeric covenant threshold from system_config, with a safe default.

        - Values are stored as strings in `system_config.config_value`
        - If the key is missing or unparsable, the provided default is returned.
        """
        try:
            result = await self.db.execute(
                select(SystemConfig.config_value).where(SystemConfig.config_key == key).limit(1)
            )
            value = result.scalar_one_or_none()
            if value is None:
                return default
            # Allow either plain numeric strings (e.g. "1.25") or percentages ("75.0")
            return Decimal(str(value))
        except Exception:
            # Never let configuration issues break covenant calculations
            return default

    async def _get_dscr_minimum(self) -> Decimal:
        """
        Get the DSCR minimum covenant threshold, overridable via `system_config`.

        Config key: `covenant_dscr_minimum`
        """
        return await self._get_config_threshold(
            key="covenant_dscr_minimum",
            default=self.DSCR_COVENANT_MINIMUM,
        )

    async def _get_ltv_maximum(self) -> Decimal:
        """
        Get the LTV maximum covenant threshold, overridable via `system_config`.

        Config key: `covenant_ltv_maximum`
        """
        return await self._get_config_threshold(
            key="covenant_ltv_maximum",
            default=self.LTV_COVENANT_MAXIMUM,
        )

    async def _get_icr_minimum(self) -> Decimal:
        """
        Get the Interest Coverage Ratio minimum covenant threshold.

        Config key: `covenant_icr_minimum`
        """
        return await self._get_config_threshold(
            key="covenant_icr_minimum",
            default=self.ICR_MINIMUM,
        )

    async def _get_current_ratio_minimum(self) -> Decimal:
        """
        Get the Current Ratio minimum covenant threshold.

        Config key: `covenant_current_ratio_minimum`
        """
        return await self._get_config_threshold(
            key="covenant_current_ratio_minimum",
            default=self.CURRENT_RATIO_MINIMUM,
        )

    async def _get_quick_ratio_minimum(self) -> Decimal:
        """
        Get the Quick Ratio minimum covenant threshold.

        Config key: `covenant_quick_ratio_minimum`
        """
        return await self._get_config_threshold(
            key="covenant_quick_ratio_minimum",
            default=self.QUICK_RATIO_MINIMUM,
        )

    async def calculate_all_covenants(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Calculate all covenant metrics for a property/period.

        Args:
            property_id: Property UUID
            period_id: Financial period UUID

        Returns:
            Complete covenant compliance analysis
        """

        # Calculate each covenant metric
        dscr_result = await self.calculate_dscr(property_id, period_id)
        ltv_result = await self.calculate_ltv_ratio(property_id, period_id)
        icr_result = await self.calculate_interest_coverage_ratio(property_id, period_id)
        liquidity_result = await self.calculate_liquidity_ratios(property_id, period_id)

        # Determine overall compliance status
        breaches = []
        warnings = []

        if not dscr_result['in_compliance']:
            breaches.append('DSCR')
        elif dscr_result['status'] == 'YELLOW':
            warnings.append('DSCR')

        if not ltv_result['in_compliance']:
            breaches.append('LTV')
        elif ltv_result['status'] == 'YELLOW':
            warnings.append('LTV')

        if not icr_result['in_compliance']:
            breaches.append('ICR')

        if not liquidity_result['current_ratio_compliant']:
            warnings.append('Current Ratio')

        # Overall status
        if breaches:
            overall_status = 'RED'
        elif warnings:
            overall_status = 'YELLOW'
        else:
            overall_status = 'GREEN'

        return {
            'property_id': str(property_id),
            'period_id': str(period_id),
            'overall_compliance_status': overall_status,
            'covenant_breaches': breaches,
            'covenant_warnings': warnings,
            'dscr': dscr_result,
            'ltv': ltv_result,
            'interest_coverage': icr_result,
            'liquidity': liquidity_result,
            'tested_at': datetime.now().isoformat()
        }

    async def calculate_dscr(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Rule A-7.1: Debt Service Coverage Ratio

        DSCR = Net Operating Income / Annual Debt Service

        Where:
        - NOI = Total Income - Total Operating Expenses
        - Annual Debt Service = Principal + Interest payments for year

        Covenant typically requires DSCR ≥ 1.25x
        This means property generates 25% more cash than debt obligations.

        Status levels:
        - ≥1.50: STRONG (GREEN)
        - 1.25-1.49: ADEQUATE (GREEN)
        - 1.15-1.24: WARNING (YELLOW)
        - 1.00-1.14: CRITICAL (RED)
        - <1.00: DEFAULT RISK (RED)

        Args:
            property_id: Property UUID
            period_id: Financial period UUID

        Returns:
            DSCR analysis with trend
        """

        # Get NOI from income statement
        noi_query = text("""
            SELECT period_amount
            FROM income_statement_data
            WHERE property_id = :property_id
            AND period_id = :period_id
            AND account_code = 'NOI_SUMMARY'
            LIMIT 1
        """)

        noi_result = await self.db.execute(
            noi_query,
            {"property_id": property_id, "period_id": period_id}
        )
        noi_row = noi_result.fetchone()

        if not noi_row:
            # Calculate NOI from detailed accounts (exclude totals/subtotals)
            noi_calc_query = text("""
                SELECT
                    SUM(CASE WHEN account_code LIKE '4%' THEN period_amount ELSE 0 END) as total_income,
                    SUM(CASE WHEN account_code LIKE '5%' THEN period_amount ELSE 0 END) as total_expenses
                FROM income_statement_data
                WHERE property_id = :property_id
                AND period_id = :period_id
                AND (is_total IS NOT TRUE OR is_total IS NULL)
                AND (is_subtotal IS NOT TRUE OR is_subtotal IS NULL)
            """)

            noi_calc_result = await self.db.execute(
                noi_calc_query,
                {"property_id": property_id, "period_id": period_id}
            )
            calc_row = noi_calc_result.fetchone()

            total_income = float(calc_row[0]) if calc_row and calc_row[0] else 0
            total_expenses = float(calc_row[1]) if calc_row and calc_row[1] else 0
            noi = total_income - total_expenses
        else:
            noi = float(noi_row[0]) if noi_row[0] else 0

        # Annualize NOI if this is a monthly period
        period_query = text("""
            SELECT period_start_date, period_end_date
            FROM financial_periods
            WHERE id = :period_id
        """)
        period_result = await self.db.execute(period_query, {"period_id": period_id})
        period_row = period_result.fetchone()

        if period_row and period_row[0] and period_row[1]:
            period_days = (period_row[1] - period_row[0]).days + 1
            period_type = 'annual' if period_days >= 330 else 'monthly'
        else:
            period_type = 'monthly'

        if period_type == 'monthly':
            annual_noi = noi * 12
        else:
            annual_noi = noi

        # Get annual debt service from mortgage statement
        debt_service_query = text("""
            SELECT
                SUM(annual_debt_service) as annual_debt_service,
                SUM(monthly_debt_service) as monthly_debt_service,
                SUM(COALESCE(principal_due, 0) + COALESCE(interest_due, 0)) as period_debt_service
            FROM mortgage_statement_data
            WHERE property_id = :property_id
            AND period_id = :period_id
        """)

        debt_result = await self.db.execute(
            debt_service_query,
            {"property_id": property_id, "period_id": period_id}
        )
        debt_row = debt_result.fetchone()

        annual_debt_service = float(debt_row[0]) if debt_row and debt_row[0] else 0
        monthly_debt_service = float(debt_row[1]) if debt_row and debt_row[1] else 0
        period_debt_service = float(debt_row[2]) if debt_row and debt_row[2] else 0

        if annual_debt_service <= 0:
            base_debt_service = monthly_debt_service or period_debt_service
            annual_debt_service = base_debt_service * 12 if period_type == 'monthly' else base_debt_service

        # Calculate DSCR
        if annual_debt_service > 0:
            dscr = annual_noi / annual_debt_service
        else:
            dscr = 0

        # Covenant: per-property covenant_thresholds first, else system_config
        covenant_threshold = await resolve_covenant_threshold_async(
            self.db, int(property_id), int(period_id), "DSCR"
        )
        covenant_threshold_f = float(covenant_threshold)
        cushion = dscr - covenant_threshold_f
        cushion_pct = (cushion / covenant_threshold_f) * 100 if covenant_threshold_f > 0 else 0

        # Determine status and compliance
        if dscr >= self.DSCR_STRONG:
            status = 'GREEN'
            interpretation = 'Strong debt coverage'
            in_compliance = True
        elif dscr >= self.DSCR_ADEQUATE:
            status = 'GREEN'
            interpretation = 'Adequate debt coverage'
            in_compliance = True
        elif dscr >= self.DSCR_WARNING:
            status = 'YELLOW'
            interpretation = 'Warning - approaching covenant minimum'
            in_compliance = True  # Still compliant but risky
        elif dscr >= self.DSCR_CRITICAL:
            status = 'RED'
            interpretation = 'CRITICAL - below covenant minimum'
            in_compliance = False
        else:
            status = 'RED'
            interpretation = 'CRITICAL - insufficient cash flow for debt service'
            in_compliance = False

        # Get trend (compare to prior 3 months)
        trend = await self._calculate_dscr_trend(property_id, period_id)

        return {
            'dscr': round(dscr, 2),
            'annual_noi': round(annual_noi, 2),
            'annual_debt_service': round(annual_debt_service, 2),
            'covenant_threshold': covenant_threshold,
            'cushion': round(cushion, 2),
            'cushion_pct': round(cushion_pct, 2),
            'status': status,
            'trend': trend,
            'in_compliance': in_compliance,
            'interpretation': interpretation,
            'requires_lender_notification': not in_compliance
        }

    async def calculate_ltv_ratio(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Rule A-7.2: Loan-to-Value Ratio

        LTV = Mortgage Balance / Property Value

        Covenant typically requires LTV ≤ 75%
        Measures leverage and collateral coverage.

        Status levels:
        - ≤65%: CONSERVATIVE (GREEN)
        - 66-70%: ADEQUATE (GREEN)
        - 71-74%: WARNING (YELLOW)
        - ≥75%: BREACH (RED)

        Args:
            property_id: Property UUID
            period_id: Financial period UUID

        Returns:
            LTV analysis with trend
        """

        # Get mortgage balance - try multiple sources
        # 1. Try mortgage statement first (most accurate)
        mortgage_stmt_query = text("""
            SELECT total_loan_balance
            FROM mortgage_statement_data
            WHERE property_id = :property_id
            AND period_id = :period_id
            LIMIT 1
        """)
        
        stmt_result = await self.db.execute(
            mortgage_stmt_query,
            {"property_id": property_id, "period_id": period_id}
        )
        stmt_row = stmt_result.fetchone()
        
        if stmt_row and stmt_row[0] and float(stmt_row[0]) > 0:
            mortgage_balance = float(stmt_row[0])
        else:
            # 2. Fall back to Balance Sheet - look for loan/mortgage liabilities
            mortgage_query = text("""
                SELECT amount
                FROM balance_sheet_data
                WHERE property_id = :property_id
                AND period_id = :period_id
                AND account_code LIKE '2%'
                AND (
                    account_name ILIKE '%loan%'
                    OR account_name ILIKE '%mortgage%'
                    OR account_name ILIKE '%note%payable%'
                    OR account_code LIKE '219%'
                    OR account_code LIKE '221%'
                )
                ORDER BY ABS(amount) DESC
                LIMIT 1
            """)
            
            mortgage_result = await self.db.execute(
                mortgage_query,
                {"property_id": property_id, "period_id": period_id}
            )
            mortgage_row = mortgage_result.fetchone()
            mortgage_balance = abs(float(mortgage_row[0])) if mortgage_row and mortgage_row[0] else 0

        # Get property value (from property table or latest appraisal)
        property_query = text("""
            SELECT
                purchase_price,
                acquisition_costs
            FROM properties
            WHERE id = :property_id
        """)

        property_result = await self.db.execute(
            property_query,
            {"property_id": property_id}
        )
        property_row = property_result.fetchone()

        if property_row and property_row[0]:
            property_value = float(property_row[0])
        else:
            # Fallback: use fixed assets from balance sheet as proxy
            assets_query = text("""
                SELECT SUM(amount)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                AND period_id = :period_id
                AND (
                    account_code LIKE '15%'
                    OR account_code LIKE '16%'
                )
            """)
            
            assets_result = await self.db.execute(
                assets_query,
                {"property_id": property_id, "period_id": period_id}
            )
            assets_row = assets_result.fetchone()
            property_value = float(assets_row[0]) if assets_row and assets_row[0] else 0

        # Calculate LTV
        if property_value > 0:
            ltv_ratio = (mortgage_balance / property_value) * 100
        else:
            ltv_ratio = None

        # Covenant: per-property covenant_thresholds first (LTV stored as percent), else system_config
        covenant_threshold_raw = await get_covenant_threshold_async(
            self.db, int(property_id), int(period_id), "LTV"
        )
        covenant_threshold = (
            await self._get_ltv_maximum()
            if covenant_threshold_raw is None
            else Decimal(str(covenant_threshold_raw))
        )
        if ltv_ratio is not None:
            covenant_threshold_f = float(covenant_threshold)
            cushion = covenant_threshold_f - ltv_ratio
            cushion_pct = (cushion / covenant_threshold_f) * 100 if covenant_threshold_f > 0 else 0
        else:
            cushion = 0.0
            cushion_pct = 0.0

        # Determine status
        if ltv_ratio is not None:
             if ltv_ratio <= self.LTV_CONSERVATIVE:
                status = 'GREEN'
                interpretation = 'Conservative leverage'
                in_compliance = True
             elif ltv_ratio <= self.LTV_WARNING:
                status = 'GREEN'
                interpretation = 'Adequate leverage'
                in_compliance = True
             elif ltv_ratio < self.LTV_CRITICAL:
                status = 'YELLOW'
                interpretation = 'Warning - approaching LTV covenant'
                in_compliance = True
             elif ltv_ratio == self.LTV_CRITICAL:
                status = 'YELLOW'
                interpretation = 'At LTV covenant limit'
                in_compliance = True
             else:
                status = 'RED'
                interpretation = 'CRITICAL - exceeds LTV covenant'
                in_compliance = False
        else:
             status = 'YELLOW' # Warning state for missing data
             interpretation = 'Unable to calculate LTV - missing property value'
             in_compliance = True # Assume compliant if unknown

        # Get trend
        trend = await self._calculate_ltv_trend(property_id, period_id)

        return {
            'ltv_ratio': round(ltv_ratio, 2) if ltv_ratio is not None else None,
            'mortgage_balance': round(mortgage_balance, 2),
            'property_value': round(property_value, 2),
            'covenant_threshold': covenant_threshold,
            'cushion': round(cushion, 2),
            'cushion_pct': round(cushion_pct, 2),
            'status': status,
            'trend': trend,
            'in_compliance': in_compliance,
            'interpretation': interpretation
        }

    async def calculate_interest_coverage_ratio(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Rule A-7.3: Interest Coverage Ratio

        ICR = EBITDA / Interest Expense

        Or simplified for real estate:
        ICR = NOI / Interest Expense

        Covenant typically requires ICR ≥ 2.0x
        Measures ability to pay interest from operations.

        Args:
            property_id: Property UUID
            period_id: Financial period UUID

        Returns:
            ICR analysis
        """

        # Get NOI (already calculated in DSCR method, reuse logic)
        # Exclude total and subtotal rows
        noi_query = text("""
            SELECT
                SUM(CASE WHEN account_code LIKE '4%' THEN period_amount ELSE 0 END) as total_income,
                SUM(CASE WHEN account_code LIKE '5%' THEN period_amount ELSE 0 END) as total_expenses
            FROM income_statement_data
            WHERE property_id = :property_id
            AND period_id = :period_id
            AND (is_total IS NOT TRUE OR is_total IS NULL)
            AND (is_subtotal IS NOT TRUE OR is_subtotal IS NULL)
        """)

        noi_result = await self.db.execute(
            noi_query,
            {"property_id": property_id, "period_id": period_id}
        )
        noi_row = noi_result.fetchone()

        total_income = float(noi_row[0]) if noi_row and noi_row[0] else 0
        total_expenses = float(noi_row[1]) if noi_row and noi_row[1] else 0
        noi = total_income - total_expenses

        # Annualize NOI if period is monthly
        period_query = text("""
            SELECT period_start_date, period_end_date
            FROM financial_periods
            WHERE id = :period_id
        """)
        period_result = await self.db.execute(period_query, {"period_id": period_id})
        period_row = period_result.fetchone()
        
        if period_row and period_row[0] and period_row[1]:
            period_days = (period_row[1] - period_row[0]).days + 1
            period_type = 'annual' if period_days >= 330 else 'monthly'
        else:
            period_type = 'monthly'
        
        if period_type == 'monthly':
            annual_noi = noi * 12
        else:
            annual_noi = noi

        # Get interest expense from mortgage statement (more accurate than IS)
        # Use YTD interest paid for annual comparison
        interest_query = text("""
            SELECT ytd_interest_paid, interest_due
            FROM mortgage_statement_data
            WHERE property_id = :property_id
            AND period_id = :period_id
            LIMIT 1
        """)

        interest_result = await self.db.execute(
            interest_query,
            {"property_id": property_id, "period_id": period_id}
        )
        interest_row = interest_result.fetchone()
        
        # Use YTD interest (annual) or annualize monthly interest due
        if interest_row and interest_row[0]:
            interest_expense = float(interest_row[0])  # YTD interest
        elif interest_row and interest_row[1]:
            # Annualize monthly interest
            interest_expense = float(interest_row[1]) * 12 if period_type == 'monthly' else float(interest_row[1])
        else:
            # Fallback: try to find in income statement (interest expense accounts)
            fallback_query = text("""
                SELECT period_amount
                FROM income_statement_data
                WHERE property_id = :property_id
                AND period_id = :period_id
                AND (
                    account_code LIKE '5%'
                    AND account_name ILIKE '%interest%expense%'
                )
                LIMIT 1
            """)
            fallback_result = await self.db.execute(
                fallback_query,
                {"property_id": property_id, "period_id": period_id}
            )
            fallback_row = fallback_result.fetchone()
            interest_expense = float(fallback_row[0]) * 12 if fallback_row and fallback_row[0] and period_type == 'monthly' else (float(fallback_row[0]) if fallback_row and fallback_row[0] else 0)

        # Calculate ICR using annualized values
        if interest_expense > 0:
            icr = annual_noi / interest_expense
        else:
            icr = 0

        # Determine compliance using configurable ICR minimum
        icr_minimum = await self._get_icr_minimum()
        icr_minimum_f = float(icr_minimum)
        in_compliance = icr >= icr_minimum_f
        
        # Determine status based on ICR value
        if icr >= float(self.ICR_STRONG):
            status = 'GREEN'
            interpretation = 'Strong interest coverage'
        elif icr >= self.ICR_MINIMUM:
            status = 'YELLOW'
            interpretation = 'Adequate interest coverage'
        else:
            status = 'RED'
            interpretation = 'CRITICAL - insufficient interest coverage'

        return {
            'interest_coverage_ratio': round(icr, 2),
            'noi': round(annual_noi, 2),
            'interest_expense': round(interest_expense, 2),
            'covenant_threshold': icr_minimum_f,
            'in_compliance': in_compliance,
            'status': status,
            'interpretation': interpretation
        }

    async def calculate_liquidity_ratios(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Rule A-7.4: Liquidity Ratios

        Current Ratio = Current Assets / Current Liabilities
        Quick Ratio = (Current Assets - Inventory) / Current Liabilities

        Covenants typically require:
        - Current Ratio ≥ 1.5
        - Quick Ratio ≥ 1.0

        Args:
            property_id: Property UUID
            period_id: Financial period UUID

        Returns:
            Liquidity analysis
        """

        # Get current assets and liabilities from balance sheet
        # Use account code ranges since category/subcategory fields are often NULL
        # Current Assets: 11xx-14xx (Cash, AR, Prepaids, Deposits, Escrow)
        # Current Liabilities: 20xx-21xx (AP, Accrued Expenses, Short-term debt)
        liquidity_query = text("""
            SELECT
                SUM(CASE 
                    WHEN account_code LIKE '11%' 
                        OR account_code LIKE '12%' 
                        OR account_code LIKE '13%' 
                        OR account_code LIKE '14%' 
                    THEN amount 
                    ELSE 0 
                END) as current_assets,
                SUM(CASE 
                    WHEN account_code LIKE '20%' 
                        OR account_code LIKE '21%' 
                    THEN ABS(amount)
                    ELSE 0 
                END) as current_liabilities,
                SUM(CASE WHEN account_name ILIKE '%INVENTORY%' THEN amount ELSE 0 END) as inventory
            FROM balance_sheet_data
            WHERE property_id = :property_id
            AND period_id = :period_id
        """)

        liq_result = await self.db.execute(
            liquidity_query,
            {"property_id": property_id, "period_id": period_id}
        )
        liq_row = liq_result.fetchone()

        current_assets = float(liq_row[0]) if liq_row and liq_row[0] else 0
        current_liabilities = float(liq_row[1]) if liq_row and liq_row[1] else 0
        inventory = float(liq_row[2]) if liq_row and liq_row[2] else 0

        # Calculate ratios
        if current_liabilities > 0:
            current_ratio = current_assets / current_liabilities
            quick_ratio = (current_assets - inventory) / current_liabilities
        else:
            current_ratio = 0.0
            quick_ratio = 0.0

        # Allow liquidity thresholds to be configured
        current_min = float(await self._get_current_ratio_minimum())
        quick_min = float(await self._get_quick_ratio_minimum())

        return {
            'current_ratio': round(current_ratio, 2),
            'quick_ratio': round(quick_ratio, 2),
            'current_assets': round(current_assets, 2),
            'current_liabilities': round(current_liabilities, 2),
            'current_ratio_compliant': current_ratio >= current_min,
            'quick_ratio_compliant': quick_ratio >= quick_min
        }

    async def _calculate_dscr_trend(
        self,
        property_id: UUID,
        current_period_id: UUID
    ) -> str:
        """
        Calculate DSCR trend over last 3 months.

        Returns:
            "UP", "DOWN", or "STABLE"
        """

        # Get last 3 periods DSCR values
        # TODO: Implement historical DSCR lookup
        # For now, return STABLE
        return "STABLE"

    async def _calculate_ltv_trend(
        self,
        property_id: UUID,
        current_period_id: UUID
    ) -> str:
        """
        Calculate LTV trend over last 3 months.

        Returns:
            "UP", "DOWN", or "STABLE"
        """

        # Get last 3 periods LTV values
        # TODO: Implement historical LTV lookup
        # For now, return STABLE
        return "STABLE"

    async def save_covenant_compliance_results(
        self,
        property_id: UUID,
        period_id: UUID,
        results: Dict[str, Any]
    ) -> None:
        """
        Save covenant compliance results to database.

        Args:
            property_id: Property UUID
            period_id: Financial period UUID
            results: Complete covenant compliance results
        """

        dscr = results['dscr']
        ltv = results['ltv']
        icr = results['interest_coverage']
        liq = results['liquidity']

        insert_query = text("""
            INSERT INTO covenant_compliance_tracking (
                property_id,
                period_id,
                dscr,
                dscr_covenant_threshold,
                dscr_cushion,
                dscr_status,
                dscr_trend,
                ltv_ratio,
                ltv_covenant_threshold,
                ltv_cushion,
                ltv_status,
                ltv_trend,
                interest_coverage_ratio,
                current_ratio,
                quick_ratio,
                overall_compliance_status,
                created_at
            ) VALUES (
                :property_id,
                :period_id,
                :dscr,
                :dscr_covenant,
                :dscr_cushion,
                :dscr_status,
                :dscr_trend,
                :ltv,
                :ltv_covenant,
                :ltv_cushion,
                :ltv_status,
                :ltv_trend,
                :icr,
                :current_ratio,
                :quick_ratio,
                :overall_status,
                NOW()
            )
            ON CONFLICT (property_id, period_id)
            DO UPDATE SET
                dscr = EXCLUDED.dscr,
                dscr_cushion = EXCLUDED.dscr_cushion,
                dscr_status = EXCLUDED.dscr_status,
                ltv_ratio = EXCLUDED.ltv_ratio,
                ltv_cushion = EXCLUDED.ltv_cushion,
                ltv_status = EXCLUDED.ltv_status,
                overall_compliance_status = EXCLUDED.overall_compliance_status,
                updated_at = NOW()
        """)

        await self.db.execute(
            insert_query,
            {
                "property_id": str(property_id),
                "period_id": str(period_id),
                "dscr": dscr['dscr'],
                "dscr_covenant": dscr['covenant_threshold'],
                "dscr_cushion": dscr['cushion'],
                "dscr_status": dscr['status'],
                "dscr_trend": dscr['trend'],
                "ltv": ltv['ltv_ratio'],
                "ltv_covenant": ltv['covenant_threshold'],
                "ltv_cushion": ltv['cushion'],
                "ltv_status": ltv['status'],
                "ltv_trend": ltv['trend'],
                "icr": icr['interest_coverage_ratio'],
                "current_ratio": liq['current_ratio'],
                "quick_ratio": liq['quick_ratio'],
                "overall_status": results['overall_compliance_status']
            }
        )

        await self.db.commit()
