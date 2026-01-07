"""
MetricsService - Financial Metrics Calculation Engine

Automatically calculates all 35 financial KPIs from extracted data
Includes balance sheet ratios, income statement margins, rent roll occupancy, and performance metrics
Designed for 100% data quality with zero division protection
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Optional
from decimal import Decimal

from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.rent_roll_data import RentRollData
from app.models.mortgage_statement_data import MortgageStatementData
from app.models.financial_metrics import FinancialMetrics
from app.core.constants import financial_thresholds, account_codes


class MetricsService:
    """
    Calculate comprehensive financial metrics from extracted data
    
    Supports all 4 document types:
    - Balance Sheet → Assets, liabilities, equity, ratios
    - Income Statement → Revenue, expenses, margins
    - Cash Flow → Operating, investing, financing flows
    - Rent Roll → Occupancy, units, rent totals
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_all_metrics(
        self, 
        property_id: int, 
        period_id: int
    ) -> FinancialMetrics:
        """
        Calculate ALL available metrics for a property/period
        
        Intelligently aggregates from all available financial statements
        Handles missing data gracefully
        
        Args:
            property_id: Property ID
            period_id: Financial Period ID
        
        Returns:
            FinancialMetrics: Calculated metrics record
        """
        metrics_data = {}
        
        # Balance Sheet Metrics (if data exists)
        if self._has_balance_sheet_data(property_id, period_id):
            metrics_data.update(self.calculate_balance_sheet_metrics(property_id, period_id))
        
        # Income Statement Metrics (if data exists)
        if self._has_income_statement_data(property_id, period_id):
            metrics_data.update(self.calculate_income_statement_metrics(property_id, period_id))
        else:
            # Clear income statement fields if no data (prevent stale values)
            # Exception: Don't clear NOI if we have mortgage data (needed for DSCR)
            # It will be preserved from database and used in mortgage calculations
            clear_noi = not self._has_mortgage_data(property_id, period_id)

            metrics_data.update({
                'total_revenue': None,
                'total_expenses': None,
                'gross_revenue': None,
                'operating_expenses': None,
                'net_operating_income': None if clear_noi else 'PRESERVE',  # Special marker
                'net_income': None,
                'operating_margin': None,
                'profit_margin': None
            })
        
        # Cash Flow Metrics (if data exists)
        if self._has_cash_flow_data(property_id, period_id):
            metrics_data.update(self.calculate_cash_flow_metrics(property_id, period_id))
        else:
            # Clear cash flow fields if no data (prevent stale values)
            metrics_data.update({
                'operating_cash_flow': None,
                'investing_cash_flow': None,
                'financing_cash_flow': None,
                'net_cash_flow': None,
                'beginning_cash_balance': None,
                'ending_cash_balance': None
            })

        # Rent Roll Metrics (if data exists)
        if self._has_rent_roll_data(property_id, period_id):
            metrics_data.update(self.calculate_rent_roll_metrics(property_id, period_id))
        else:
            # Clear rent roll fields if no data (prevent stale values)
            metrics_data.update({
                'total_units': None,
                'occupied_units': None,
                'vacant_units': None,
                'occupancy_rate': None,
                'total_leasable_sqft': None,
                'occupied_sqft': None,
                'total_monthly_rent': None,
                'total_annual_rent': None
            })
        
        # Performance Metrics (requires both IS and RR data)
        if self._has_income_statement_data(property_id, period_id) and self._has_rent_roll_data(property_id, period_id):
            metrics_data.update(self.calculate_performance_metrics(property_id, period_id, metrics_data))
        
        # Mortgage Metrics (if mortgage data exists)
        if self._has_mortgage_data(property_id, period_id):
            # If NOI not yet in metrics_data or is marked for preservation, get from database
            # (it might have been calculated in a previous period or entered manually)
            if ('net_operating_income' not in metrics_data or
                metrics_data['net_operating_income'] is None or
                metrics_data['net_operating_income'] == 'PRESERVE'):

                existing_metrics_record = self.db.query(FinancialMetrics).filter(
                    FinancialMetrics.property_id == property_id,
                    FinancialMetrics.period_id == period_id
                ).first()
                if existing_metrics_record and existing_metrics_record.net_operating_income:
                    metrics_data['net_operating_income'] = existing_metrics_record.net_operating_income
                else:
                    # If no existing NOI, set to None (can't calculate DSCR)
                    metrics_data['net_operating_income'] = None

            metrics_data.update(self.calculate_mortgage_metrics(property_id, period_id, metrics_data))
        
        # Store metrics (upsert)
        metrics = self._store_metrics(property_id, period_id, metrics_data)
        
        return metrics
    
    # ==================== BALANCE SHEET METRICS ====================
    
    def calculate_balance_sheet_metrics(
        self, 
        property_id: int, 
        period_id: int
    ) -> Dict:
        """
        Calculate comprehensive balance sheet metrics (Template v1.0 compliant)
        
        Calculates ALL Template v1.0 metrics:
        - Balance sheet totals (8 metrics)
        - Liquidity metrics (4 metrics)
        - Leverage metrics (4 metrics)
        - Property metrics (7 metrics)
        - Cash analysis (3 metrics)
        - Receivables analysis (5 metrics)
        - Debt analysis (6 metrics)
        - Equity analysis (7 metrics)
        
        Total: 44 balance sheet metrics
        """
        metrics = {}
        
        # Get all balance sheet totals
        metrics.update(self._calculate_balance_sheet_totals(property_id, period_id))
        
        # Calculate Template v1.0 metric categories
        metrics.update(self._calculate_liquidity_metrics(property_id, period_id, metrics))
        metrics.update(self._calculate_leverage_metrics(property_id, period_id, metrics))
        metrics.update(self._calculate_property_metrics(property_id, period_id))
        metrics.update(self._calculate_cash_analysis(property_id, period_id))
        metrics.update(self._calculate_receivables_analysis(property_id, period_id, metrics))
        metrics.update(self._calculate_debt_analysis(property_id, period_id))
        metrics.update(self._calculate_equity_analysis(property_id, period_id))
        
        return metrics
    
    def _calculate_balance_sheet_totals(self, property_id: int, period_id: int) -> Dict:
        """Get all balance sheet section totals"""
        return {
            "total_assets": self._get_balance_sheet_account(property_id, period_id, '1999-0000'),
            "total_current_assets": self._get_balance_sheet_account(property_id, period_id, '0499-9000'),
            "total_property_equipment": self._get_balance_sheet_account(property_id, period_id, '1099-0000'),
            "total_other_assets": self._get_balance_sheet_account(property_id, period_id, '1998-0000'),
            "total_liabilities": self._get_balance_sheet_account(property_id, period_id, '2999-0000'),
            "total_current_liabilities": self._get_balance_sheet_account(property_id, period_id, '2590-0000'),
            "total_long_term_liabilities": self._get_balance_sheet_account(property_id, period_id, '2900-0000'),
            "total_equity": self._get_balance_sheet_account(property_id, period_id, '3999-0000'),
        }
    
    def _calculate_liquidity_metrics(self, property_id: int, period_id: int, totals: Dict) -> Dict:
        """
        Calculate liquidity metrics (Template v1.0)
        
        Metrics:
        - Current Ratio: Current Assets / Current Liabilities
        - Quick Ratio: (Current Assets - Receivables) / Current Liabilities
        - Cash Ratio: Total Cash / Current Liabilities
        - Working Capital: Current Assets - Current Liabilities
        """
        current_assets = totals.get("total_current_assets") or Decimal('0')
        current_liabilities = totals.get("total_current_liabilities") or Decimal('0')
        
        # Get total receivables for quick ratio
        total_receivables = self._sum_balance_sheet_accounts_by_codes(
            property_id, period_id, ['0305-0000', '0306-0000', '0307-0000']
        )
        
        # Get total cash for cash ratio
        total_cash = self._sum_balance_sheet_accounts_by_range(
            property_id, period_id, '0122', '0127'  # Cash accounts 0122-0127
        )
        
        return {
            "current_ratio": self.safe_divide(current_assets, current_liabilities),
            "quick_ratio": self.safe_divide(current_assets - total_receivables, current_liabilities),
            "cash_ratio": self.safe_divide(total_cash, current_liabilities),
            "working_capital": current_assets - current_liabilities,
        }
    
    def _calculate_leverage_metrics(self, property_id: int, period_id: int, totals: Dict) -> Dict:
        """
        Calculate leverage metrics (Template v1.0)

        Metrics:
        - Debt-to-Assets Ratio: Total Liabilities / Total Assets
        - Debt-to-Equity Ratio: Total Liabilities / Total Equity
        - Equity Ratio: Total Equity / Total Assets
        - LTV Ratio: Total Loan Balance (from mortgage data) / Net Property Value
        """
        total_assets = totals.get("total_assets") or Decimal('0')
        total_liabilities = totals.get("total_liabilities") or Decimal('0')
        total_equity = totals.get("total_equity") or Decimal('0')

        # Get property value - use total_property_equipment if available, otherwise use net_property_value from existing metrics
        net_property_value = totals.get("total_property_equipment")
        if not net_property_value or net_property_value == Decimal('0'):
            # Fallback to net_property_value from existing financial_metrics record
            existing_metrics = self.db.query(FinancialMetrics).filter(
                FinancialMetrics.property_id == property_id,
                FinancialMetrics.period_id == period_id
            ).first()
            if existing_metrics and existing_metrics.net_property_value:
                net_property_value = existing_metrics.net_property_value
            else:
                net_property_value = Decimal('0')

        # Get loan balance from mortgage statement data (preferred) or balance sheet
        loan_balance = self._get_loan_balance_from_mortgage(property_id, period_id)
        if loan_balance == Decimal('0'):
            # Fallback to balance sheet long-term debt if mortgage data not available
            loan_balance = totals.get("total_long_term_liabilities") or Decimal('0')

        return {
            "debt_to_assets_ratio": self.safe_divide(total_liabilities, total_assets),
            "debt_to_equity_ratio": self.safe_divide(total_liabilities, total_equity),
            "equity_ratio": self.safe_divide(total_equity, total_assets),
            "ltv_ratio": self.safe_divide(loan_balance, net_property_value),
        }
    
    def _calculate_property_metrics(self, property_id: int, period_id: int) -> Dict:
        """
        Calculate property metrics (Template v1.0)
        
        Metrics:
        - Gross Property Value: Sum of all gross property accounts (0510-0950)
        - Accumulated Depreciation: Sum of all accumulated depreciation (1061-1091)
        - Net Property Value: Gross - Accumulated
        - Depreciation Rate: Accumulated / Gross
        - Land Value: 0510-0000 (never depreciates)
        - Building Value Net: Buildings - Accumulated Depreciation
        - Improvements Value Net: Improvements - Accumulated Depreciation
        """
        # Gross property values
        land = self._get_balance_sheet_account(property_id, period_id, '0510-0000') or Decimal('0')
        buildings = self._get_balance_sheet_account(property_id, period_id, '0610-0000') or Decimal('0')
        
        # Sum all improvement accounts (0710-0950)
        improvements_gross = self._sum_balance_sheet_accounts_by_range(
            property_id, period_id, '0710', '0950'
        )
        
        gross_property = land + buildings + improvements_gross
        
        # Accumulated depreciation (contra-asset, should be negative)
        accum_depr = self._sum_balance_sheet_accounts_by_range(
            property_id, period_id, '1061', '1091'
        )
        
        # Specific accumulated depreciation for buildings
        accum_depr_buildings = self._get_balance_sheet_account(property_id, period_id, '1061-0000') or Decimal('0')
        
        # Net values
        net_property = gross_property + accum_depr  # accum_depr is negative
        building_value_net = buildings + accum_depr_buildings
        improvements_value_net = improvements_gross + (accum_depr - accum_depr_buildings)
        
        return {
            "gross_property_value": gross_property,
            "accumulated_depreciation": accum_depr,
            "net_property_value": net_property,
            "depreciation_rate": self.safe_divide(abs(accum_depr), gross_property),
            "land_value": land,
            "building_value_net": building_value_net,
            "improvements_value_net": improvements_value_net,
        }
    
    def _calculate_cash_analysis(self, property_id: int, period_id: int) -> Dict:
        """
        Calculate cash position analysis (Template v1.0)
        
        Metrics:
        - Operating Cash: Sum of cash accounts (0122-0125)
        - Restricted Cash: Sum of escrow accounts (1310-1340)
        - Total Cash Position: Operating + Restricted
        """
        # Operating cash accounts (0122-0125)
        operating_cash = self._sum_balance_sheet_accounts_by_range(
            property_id, period_id, '0122', '0125'
        )
        
        # Restricted cash - escrow accounts (1310-1340)
        restricted_cash = self._sum_balance_sheet_accounts_by_range(
            property_id, period_id, '1310', '1340'
        )
        
        return {
            "operating_cash": operating_cash,
            "restricted_cash": restricted_cash,
            "total_cash_position": operating_cash + restricted_cash,
        }
    
    def _calculate_receivables_analysis(self, property_id: int, period_id: int, totals: Dict) -> Dict:
        """
        Calculate receivables analysis (Template v1.0)
        
        Metrics:
        - Tenant Receivables: A/R Tenants (0305-0000)
        - Inter-company Receivables: Sum of inter-company A/R (0315-0345)
        - Other Receivables: Other A/R accounts
        - Total Receivables: Sum of all receivables
        - A/R Percentage: Total Receivables / Current Assets
        """
        tenant_ar = self._get_balance_sheet_account(property_id, period_id, '0305-0000') or Decimal('0')
        
        # Inter-company receivables (0315-0345 range)
        intercompany_ar = self._sum_balance_sheet_accounts_by_range(
            property_id, period_id, '0315', '0345'
        )
        
        # Other receivables
        other_ar = self._sum_balance_sheet_accounts_by_codes(
            property_id, period_id, ['0210-0000', '0306-0000', '0307-0000', '0310-0000', '0347-0000']
        )
        
        total_receivables = tenant_ar + intercompany_ar + other_ar
        current_assets = totals.get("total_current_assets") or Decimal('0')
        
        return {
            "tenant_receivables": tenant_ar,
            "intercompany_receivables": intercompany_ar,
            "other_receivables": other_ar,
            "total_receivables": total_receivables,
            "ar_percentage_of_assets": self.safe_divide(total_receivables, current_assets),
        }
    
    def _calculate_debt_analysis(self, property_id: int, period_id: int) -> Dict:
        """
        Calculate debt analysis (Template v1.0)
        
        Metrics:
        - Short-Term Debt: Current portion of LTD + short-term loans
        - Institutional Debt: Primary lenders (2611-2621)
        - Mezzanine Debt: Mezz financing (accounts with MEZZ)
        - Shareholder Loans: Shareholder loan accounts (2650-2671)
        - Long-Term Debt: Total long-term liabilities
        - Total Debt: Short-term + Long-term
        """
        # Short-term debt
        short_term = self._sum_balance_sheet_accounts_by_codes(
            property_id, period_id, ['2197-0000', '2411-0000']
        )
        
        # Institutional debt (2611-2621, excluding mezz)
        institutional = self._sum_balance_sheet_accounts_by_range(
            property_id, period_id, '2611', '2621'
        )
        
        # Mezzanine debt (accounts ending in -MEZZ or specific codes)
        mezzanine = self._sum_balance_sheet_accounts_by_codes(
            property_id, period_id, ['2611-1000', '2613-0000', '2618-0000']  # CIBC-MEZZ, KeyBank-Mezz, Trawler
        )
        
        # Shareholder loans (2650-2671)
        shareholder = self._sum_balance_sheet_accounts_by_range(
            property_id, period_id, '2650', '2671'
        )
        
        # Long-term debt total
        long_term = self._get_balance_sheet_account(property_id, period_id, '2900-0000') or Decimal('0')
        
        return {
            "short_term_debt": short_term,
            "institutional_debt": institutional - mezzanine,  # Exclude mezz from institutional
            "mezzanine_debt": mezzanine,
            "shareholder_loans": shareholder,
            "long_term_debt": long_term,
            "total_debt": short_term + long_term,
        }
    
    def _calculate_equity_analysis(self, property_id: int, period_id: int) -> Dict:
        """
        Calculate equity analysis (Template v1.0)
        
        Metrics:
        - Partners Contribution: 3050-0000
        - Beginning Equity: 3910-0000
        - Partners Draw: 3920-0000
        - Distributions: 3990-0000
        - Current Period Earnings: 3995-0000
        - Ending Equity: 3999-0000
        - Equity Change: Ending - Beginning
        """
        partners_contribution = self._get_balance_sheet_account(property_id, period_id, '3050-1000') or Decimal('0')
        beginning_equity = self._get_balance_sheet_account(property_id, period_id, '3910-0000') or Decimal('0')
        partners_draw = self._get_balance_sheet_account(property_id, period_id, '3920-0000') or Decimal('0')
        distributions = self._get_balance_sheet_account(property_id, period_id, '3990-0000') or Decimal('0')
        current_period_earnings = self._get_balance_sheet_account(property_id, period_id, '3995-0000') or Decimal('0')
        ending_equity = self._get_balance_sheet_account(property_id, period_id, '3999-0000') or Decimal('0')
        
        return {
            "partners_contribution": partners_contribution,
            "beginning_equity": beginning_equity,
            "partners_draw": partners_draw,
            "distributions": distributions,
            "current_period_earnings": current_period_earnings,
            "ending_equity": ending_equity,
            "equity_change": ending_equity - beginning_equity,
        }
    
    # ==================== INCOME STATEMENT METRICS ====================
    
    def calculate_income_statement_metrics(
        self, 
        property_id: int, 
        period_id: int
    ) -> Dict:
        """
        Calculate income statement metrics and margins
        
        Metrics:
        - Total revenue, total expenses
        - Net operating income (NOI)
        - Net income
        - Operating margin, profit margin
        """
        # Get totals - try specific accounts first
        total_revenue = self._get_income_statement_total(property_id, period_id, '4999-0000')
        total_expenses = self._get_income_statement_total(property_id, period_id, '8999-0000')
        stored_noi = self._get_income_statement_total(property_id, period_id, '6299-0000')
        net_income = self._get_income_statement_total(property_id, period_id, '9090-0000')
        
        # If totals not found, sum categories
        if not total_revenue:
            total_revenue = self._sum_income_statement_accounts(
                property_id, period_id, account_pattern='4%', is_calculated=False
            )
        
        if not total_expenses:
            total_expenses = self._sum_income_statement_accounts(
                property_id,
                period_id,
                account_pattern='[5-8]%',
                is_calculated=False,
                exclude_account_codes=['6299-0000']
            )
        
        # Calculate operating expenses (5xxx and 6xxx accounts only)
        # Operating expenses exclude 7xxx (mortgage interest) and 8xxx (depreciation/amortization)
        operating_expenses = self._sum_income_statement_accounts(
            property_id,
            period_id,
            account_pattern='[5-6]%',
            is_calculated=False,
            exclude_account_codes=['6299-0000']
        ) or Decimal('0')
        
        # Get gross revenue (excluding Other Income adjustments for margin calculation)
        # Other Income (4090) can have large negative adjustments that skew margins
        gross_revenue = self._sum_income_statement_accounts(
            property_id, period_id, account_pattern='4%', is_calculated=False
        )
        # Exclude Other Income (4090) if it's a large negative adjustment
        # Use configurable threshold (percentage-based or absolute value)
        other_income = self._get_income_statement_total(property_id, period_id, '4090-0000')

        # Calculate threshold as percentage of gross revenue or use absolute minimum
        threshold = (gross_revenue * financial_thresholds.noi_large_negative_adjustment_percentage
                    if gross_revenue
                    else financial_thresholds.noi_large_negative_adjustment_threshold)

        if other_income and other_income < -abs(threshold):
            gross_revenue_for_margin = gross_revenue - other_income if gross_revenue else None
        else:
            gross_revenue_for_margin = gross_revenue
        
        # Calculate NOI: Revenue - Operating Expenses
        # Prefer calculated NOI over stored NOI for accuracy
        if gross_revenue_for_margin is not None and operating_expenses is not None:
            calculated_noi = gross_revenue_for_margin - operating_expenses
            noi = calculated_noi
        elif stored_noi is not None:
            # Fall back to stored NOI if calculation not possible
            noi = stored_noi
        else:
            noi = None
        
        # Calculate operating margin using gross revenue (before large adjustments)
        # This gives a more accurate picture of operating performance
        revenue_for_margin = gross_revenue_for_margin if gross_revenue_for_margin else total_revenue
        operating_margin = self.safe_divide(noi, revenue_for_margin) * Decimal('100') if noi is not None and revenue_for_margin is not None else None
        profit_margin_calc = self.safe_divide(net_income, total_revenue)
        profit_margin = profit_margin_calc * Decimal('100') if profit_margin_calc is not None else None
        
        return {
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "net_operating_income": noi,
            "net_income": net_income,
            "operating_margin": operating_margin,
            "profit_margin": profit_margin,
        }
    
    # ==================== CASH FLOW METRICS ====================
    
    def calculate_cash_flow_metrics(
        self, 
        property_id: int, 
        period_id: int
    ) -> Dict:
        """
        Calculate cash flow metrics - Template v1.0 compliant
        
        Metrics from CashFlowHeader:
        - Total income, expenses, NOI
        - Net income and cash flow
        - Beginning and ending cash balances
        - All percentages
        - Operating, investing, financing flows (if categorized)
        """
        from app.models.cash_flow_header import CashFlowHeader
        from app.models.cash_account_reconciliation import CashAccountReconciliation
        
        # Calculate cash flow activities from categorized line items
        operating_cf = self._sum_cash_flow_by_category(property_id, period_id, 'operating')
        investing_cf = self._sum_cash_flow_by_category(property_id, period_id, 'investing')
        financing_cf = self._sum_cash_flow_by_category(property_id, period_id, 'financing')
        
        # Net cash flow
        net_cf = (operating_cf or Decimal('0')) + (investing_cf or Decimal('0')) + (financing_cf or Decimal('0'))
        
        # Get header for additional data (if exists)
        header = self.db.query(CashFlowHeader).filter(
            CashFlowHeader.property_id == property_id,
            CashFlowHeader.period_id == period_id
        ).first()
        
        # Try to get cash balances from reconciliation records
        total_cash_row = self.db.query(CashAccountReconciliation).filter(
            CashAccountReconciliation.property_id == property_id,
            CashAccountReconciliation.period_id == period_id,
            CashAccountReconciliation.is_total_row == True
        ).first()
        
        beginning_cash = total_cash_row.beginning_balance if total_cash_row else (header.beginning_cash_balance if header else None)
        ending_cash = total_cash_row.ending_balance if total_cash_row else (header.ending_cash_balance if header else None)
        
        return {
            "operating_cash_flow": operating_cf,
            "investing_cash_flow": investing_cf,
            "financing_cash_flow": financing_cf,
            "net_cash_flow": net_cf,
            "beginning_cash_balance": beginning_cash,
            "ending_cash_balance": ending_cash,
        }
    
    # ==================== RENT ROLL METRICS ====================
    
    def calculate_rent_roll_metrics(
        self, 
        property_id: int, 
        period_id: int
    ) -> Dict:
        """
        Calculate rent roll metrics
        
        Metrics:
        - Total units, occupied/vacant units
        - Occupancy rate
        - Total leasable sqft, occupied sqft
        - Total monthly/annual rent
        - Average rent per sqft
        """
        stats = self.calculate_rent_roll_stats(property_id, period_id)
        
        # Calculate occupancy rate
        total_units = stats.get('total_units', 0)
        occupied_units = stats.get('occupied_units', 0)
        occupancy_rate = self.safe_divide(
            Decimal(str(occupied_units)), 
            Decimal(str(total_units))
        ) * Decimal('100')
        
        # Calculate average rent per sqft
        total_monthly_rent = stats.get('total_monthly_rent')
        total_leasable_sqft = stats.get('total_leasable_sqft')
        avg_rent_per_sqft = self.safe_divide(total_monthly_rent, total_leasable_sqft)
        
        return {
            "total_units": total_units,
            "occupied_units": occupied_units,
            "vacant_units": stats.get('vacant_units', 0),
            "occupancy_rate": occupancy_rate,
            "total_leasable_sqft": total_leasable_sqft,
            "occupied_sqft": stats.get('occupied_sqft'),
            "total_monthly_rent": total_monthly_rent,
            "total_annual_rent": stats.get('total_annual_rent'),
            "avg_rent_per_sqft": avg_rent_per_sqft,
        }
    
    # ==================== PERFORMANCE METRICS ====================
    
    def calculate_performance_metrics(
        self, 
        property_id: int, 
        period_id: int,
        existing_metrics: Dict
    ) -> Dict:
        """
        Calculate property performance metrics
        
        Requires both income statement and rent roll data
        
        Metrics:
        - NOI per sqft
        - Revenue per sqft
        - Expense ratio
        """
        noi = existing_metrics.get('net_operating_income')
        revenue = existing_metrics.get('total_revenue')
        expenses = existing_metrics.get('total_expenses')
        total_sqft = existing_metrics.get('total_leasable_sqft')
        
        # Per sqft metrics
        noi_per_sqft = self.safe_divide(noi, total_sqft)
        revenue_per_sqft = self.safe_divide(revenue, total_sqft)
        
        # Expense ratio
        expense_ratio_result = self.safe_divide(expenses, revenue)
        expense_ratio = expense_ratio_result * Decimal('100') if expense_ratio_result is not None else None
        
        return {
            "noi_per_sqft": noi_per_sqft,
            "revenue_per_sqft": revenue_per_sqft,
            "expense_ratio": expense_ratio,
        }
    
    # ==================== HELPER METHODS ====================
    
    def _is_special_unit_type(self, unit_number: Optional[str]) -> bool:
        """
        Check if unit is a special type that shouldn't count toward occupancy

        Uses configurable special unit types from constants
        These are not leasable units and should be excluded from occupancy calculations
        """
        return account_codes.is_special_unit_type(unit_number)
    
    def calculate_rent_roll_stats(
        self, 
        property_id: int, 
        period_id: int
    ) -> Dict:
        """
        Aggregate rent roll statistics
        
        Returns detailed statistics from rent roll data
        Excludes special unit types (COMMON, ATM, LAND, SIGN) from occupancy calculations
        """
        # Get all rent roll entries
        rent_roll = self.db.query(RentRollData).filter(
            RentRollData.property_id == property_id,
            RentRollData.period_id == period_id
        ).all()
        
        if not rent_roll:
            return {
                'total_units': 0,
                'occupied_units': 0,
                'vacant_units': 0,
                'total_leasable_sqft': None,
                'occupied_sqft': None,
                'total_monthly_rent': None,
                'total_annual_rent': None,
            }
        
        # Filter out special unit types (COMMON, ATM, LAND, SIGN) for occupancy calculations
        # These are not leasable units and shouldn't count toward occupancy
        leasable_units = [unit for unit in rent_roll if not self._is_special_unit_type(unit.unit_number)]
        
        # Count units (only leasable units count toward occupancy)
        total_units = len(leasable_units)
        occupied_units = sum(1 for unit in leasable_units if unit.occupancy_status == 'occupied')
        vacant_units = total_units - occupied_units
        
        # Sum sqft (include all units for sqft, but occupancy uses only leasable)
        total_leasable_sqft = sum(
            unit.unit_area_sqft for unit in rent_roll 
            if unit.unit_area_sqft is not None
        )
        occupied_sqft = sum(
            unit.unit_area_sqft for unit in leasable_units 
            if unit.unit_area_sqft is not None and unit.occupancy_status == 'occupied'
        )
        
        # Sum rents (include all units for rent totals)
        total_monthly_rent = sum(
            unit.monthly_rent for unit in rent_roll 
            if unit.monthly_rent is not None
        )
        total_annual_rent = sum(
            unit.annual_rent for unit in rent_roll 
            if unit.annual_rent is not None
        )
        
        # If annual not available, calculate from monthly
        if not total_annual_rent and total_monthly_rent:
            total_annual_rent = total_monthly_rent * Decimal('12')
        
        return {
            'total_units': total_units,
            'occupied_units': occupied_units,
            'vacant_units': vacant_units,
            'total_leasable_sqft': Decimal(str(total_leasable_sqft)) if total_leasable_sqft else None,
            'occupied_sqft': Decimal(str(occupied_sqft)) if occupied_sqft else None,
            'total_monthly_rent': Decimal(str(total_monthly_rent)) if total_monthly_rent else None,
            'total_annual_rent': Decimal(str(total_annual_rent)) if total_annual_rent else None,
        }
    
    def calculate_mortgage_metrics(
        self,
        property_id: int,
        period_id: int,
        existing_metrics: Dict
    ) -> Dict:
        """
        Calculate mortgage-specific metrics
        
        Metrics:
        - Total mortgage debt (sum of all principal balances)
        - Weighted average interest rate
        - Total monthly/annual debt service
        - DSCR (if NOI available)
        - Interest coverage ratio
        - Debt yield
        - Break-even occupancy
        """
        # Get all mortgage statements for this property/period
        mortgages = self.db.query(MortgageStatementData).filter(
            MortgageStatementData.property_id == property_id,
            MortgageStatementData.period_id == period_id
        ).all()

        # If no mortgage data for this specific period, use the latest available mortgage data
        if not mortgages:
            from app.models.financial_period import FinancialPeriod

            # Get the current period details to find earlier periods
            current_period = self.db.query(FinancialPeriod).filter(
                FinancialPeriod.id == period_id
            ).first()

            if current_period:
                # Find the most recent period with mortgage data that's on or before current period
                latest_mortgage_period = self.db.query(FinancialPeriod).join(
                    MortgageStatementData,
                    MortgageStatementData.period_id == FinancialPeriod.id
                ).filter(
                    FinancialPeriod.property_id == property_id,
                    # Earlier or same year/month
                    ((FinancialPeriod.period_year < current_period.period_year) |
                     ((FinancialPeriod.period_year == current_period.period_year) &
                      (FinancialPeriod.period_month <= current_period.period_month)))
                ).order_by(
                    FinancialPeriod.period_year.desc(),
                    FinancialPeriod.period_month.desc()
                ).first()

                if latest_mortgage_period:
                    mortgages = self.db.query(MortgageStatementData).filter(
                        MortgageStatementData.property_id == property_id,
                        MortgageStatementData.period_id == latest_mortgage_period.id
                    ).all()

        if not mortgages:
            return {}
        
        # Calculate total mortgage debt
        total_mortgage_debt = sum(
            Decimal(str(m.principal_balance or 0)) for m in mortgages
        )
        
        # Calculate weighted average interest rate
        total_weighted_rate = Decimal('0')
        total_principal_for_rate = Decimal('0')
        for m in mortgages:
            if m.interest_rate and m.principal_balance:
                principal = Decimal(str(m.principal_balance))
                rate = Decimal(str(m.interest_rate))
                total_weighted_rate += principal * rate
                total_principal_for_rate += principal
        
        weighted_avg_interest_rate = (
            total_weighted_rate / total_principal_for_rate
            if total_principal_for_rate > 0 else None
        )
        
        # Calculate total debt service
        total_monthly_debt_service = Decimal('0')
        total_annual_debt_service = Decimal('0')
        
        for m in mortgages:
            if m.annual_debt_service:
                total_annual_debt_service += Decimal(str(m.annual_debt_service))
            elif m.monthly_debt_service:
                monthly = Decimal(str(m.monthly_debt_service))
                total_monthly_debt_service += monthly
                total_annual_debt_service += monthly * Decimal('12')
            elif m.principal_due and m.interest_due:
                monthly = Decimal(str(m.principal_due or 0)) + Decimal(str(m.interest_due or 0))
                total_monthly_debt_service += monthly
                total_annual_debt_service += monthly * Decimal('12')
            elif m.total_payment_due:
                # Use total_payment_due if individual components not available
                monthly = Decimal(str(m.total_payment_due))
                total_monthly_debt_service += monthly
                total_annual_debt_service += monthly * Decimal('12')
        
        # Calculate DSCR if NOI available
        dscr = None
        noi = existing_metrics.get('net_operating_income')
        if noi and total_annual_debt_service > 0:
            dscr = Decimal(str(noi)) / total_annual_debt_service
        
        # Calculate interest coverage ratio (EBIT / Interest Expense)
        interest_coverage_ratio = None
        if noi:
            total_interest = sum(
                Decimal(str(m.ytd_interest_paid or 0)) for m in mortgages
            )
            # Annualize if needed (assume YTD is for the period)
            # For monthly periods, multiply by 12
            from app.models.financial_period import FinancialPeriod
            period = self.db.query(FinancialPeriod).filter(
                FinancialPeriod.id == period_id
            ).first()
            if period and period.period_start_date and period.period_end_date:
                days_diff = (period.period_end_date - period.period_start_date).days
                if days_diff <= 35:  # Monthly period
                    total_interest = total_interest * Decimal('12')
            
            if total_interest > 0:
                interest_coverage_ratio = Decimal(str(noi)) / total_interest
        
        # Calculate debt yield (NOI / Total Loan Amount * 100)
        debt_yield = None
        if noi and total_mortgage_debt > 0:
            debt_yield = (Decimal(str(noi)) / total_mortgage_debt) * Decimal('100')
        
        # Calculate break-even occupancy
        # Break-Even = (Operating Expenses + Debt Service) / Gross Potential Rent * 100
        break_even_occupancy = None
        total_expenses = existing_metrics.get('total_expenses') or Decimal('0')
        gross_potential_rent = existing_metrics.get('total_annual_rent')
        if gross_potential_rent and gross_potential_rent > 0:
            total_required = total_expenses + total_annual_debt_service
            break_even_occupancy = (total_required / Decimal(str(gross_potential_rent))) * Decimal('100')
        
        return {
            'total_mortgage_debt': total_mortgage_debt if total_mortgage_debt > 0 else None,
            'weighted_avg_interest_rate': weighted_avg_interest_rate,
            'total_monthly_debt_service': total_monthly_debt_service if total_monthly_debt_service > 0 else None,
            'total_annual_debt_service': total_annual_debt_service if total_annual_debt_service > 0 else None,
            'dscr': dscr,
            'interest_coverage_ratio': interest_coverage_ratio,
            'debt_yield': debt_yield,
            'break_even_occupancy': break_even_occupancy
        }
    
    def safe_divide(
        self, 
        numerator: Optional[Decimal], 
        denominator: Optional[Decimal]
    ) -> Optional[Decimal]:
        """
        Safe division with zero protection
        
        Returns None if either value is None
        Returns 0 if denominator is 0
        Otherwise returns numerator / denominator
        """
        if numerator is None or denominator is None:
            return None
        
        if denominator == 0:
            return Decimal('0')
        
        return numerator / denominator
    
    def _get_balance_sheet_account(
        self, 
        property_id: int, 
        period_id: int, 
        account_code: str
    ) -> Optional[Decimal]:
        """Query specific account from balance sheet"""
        result = self.db.query(BalanceSheetData.amount).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.period_id == period_id,
            BalanceSheetData.account_code == account_code
        ).first()
        
        return result[0] if result else None
    
    def _sum_balance_sheet_accounts(
        self, 
        property_id: int, 
        period_id: int, 
        account_code_pattern: str
    ) -> Optional[Decimal]:
        """Sum balance sheet accounts matching pattern"""
        result = self.db.query(
            func.sum(BalanceSheetData.amount)
        ).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.period_id == period_id,
            BalanceSheetData.account_code.like(account_code_pattern),
            BalanceSheetData.is_calculated == False
        ).scalar()
        
        return result if result else None
    
    def _get_income_statement_total(
        self,
        property_id: int,
        period_id: int,
        account_code: str
    ) -> Optional[Decimal]:
        """Query specific total from income statement"""
        result = self.db.query(IncomeStatementData.period_amount).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code == account_code
        ).first()

        return result[0] if result else None

    def _get_loan_balance_from_mortgage(
        self,
        property_id: int,
        period_id: int
    ) -> Decimal:
        """
        Get total loan balance from mortgage statement data

        Returns the total_loan_balance from mortgage_statement_data if available,
        otherwise returns 0.
        """
        result = self.db.query(MortgageStatementData.total_loan_balance).filter(
            MortgageStatementData.property_id == property_id,
            MortgageStatementData.period_id == period_id
        ).first()

        return Decimal(str(result[0])) if result and result[0] else Decimal('0')
    
    def _sum_income_statement_accounts(
        self, 
        property_id: int, 
        period_id: int, 
        account_pattern: str,
        is_calculated: bool = False,
        exclude_account_codes: Optional[list[str]] = None
    ) -> Optional[Decimal]:
        """Sum income statement accounts matching pattern
        
        Supports both SQL LIKE patterns (e.g., '4%') and regex patterns (e.g., '[5-8]%')
        """
        from sqlalchemy import or_

        filters = [
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.is_calculated == is_calculated
        ]
        if exclude_account_codes:
            filters.append(~IncomeStatementData.account_code.in_(exclude_account_codes))
        
        # Handle regex patterns like [5-8]% by converting to multiple LIKE conditions
        if account_pattern.startswith('[') and ']' in account_pattern:
            # Extract range and suffix
            range_end = account_pattern.index(']')
            range_part = account_pattern[1:range_end]
            suffix = account_pattern[range_end + 1:]
            
            # Parse range (e.g., '5-8' -> ['5', '6', '7', '8'])
            if '-' in range_part:
                start, end = range_part.split('-')
                start_digit = int(start)
                end_digit = int(end)
                digits = [str(d) for d in range(start_digit, end_digit + 1)]
            else:
                digits = [range_part]
            
            # Build OR conditions for each digit
            conditions = [
                IncomeStatementData.account_code.like(f"{digit}{suffix}")
                for digit in digits
            ]
            
            result = self.db.query(
                func.sum(IncomeStatementData.period_amount)
            ).filter(
                *filters,
                or_(*conditions)
            ).scalar()
        else:
            # Standard LIKE pattern
            result = self.db.query(
                func.sum(IncomeStatementData.period_amount)
            ).filter(
                *filters,
                IncomeStatementData.account_code.like(account_pattern)
            ).scalar()
        
        return result if result else None
    
    def _sum_cash_flow_by_category(
        self, 
        property_id: int, 
        period_id: int, 
        category: str
    ) -> Optional[Decimal]:
        """Sum cash flow by category (operating/investing/financing)"""
        result = self.db.query(
            func.sum(CashFlowData.period_amount)
        ).filter(
            CashFlowData.property_id == property_id,
            CashFlowData.period_id == period_id,
            CashFlowData.cash_flow_category == category
        ).scalar()
        
        return result if result else None
    
    def _has_balance_sheet_data(self, property_id: int, period_id: int) -> bool:
        """Check if balance sheet data exists"""
        count = self.db.query(func.count(BalanceSheetData.id)).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.period_id == period_id
        ).scalar()
        
        return count > 0
    
    def _has_income_statement_data(self, property_id: int, period_id: int) -> bool:
        """Check if income statement data exists"""
        count = self.db.query(func.count(IncomeStatementData.id)).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id
        ).scalar()
        
        return count > 0
    
    def _has_cash_flow_data(self, property_id: int, period_id: int) -> bool:
        """Check if cash flow data exists"""
        count = self.db.query(func.count(CashFlowData.id)).filter(
            CashFlowData.property_id == property_id,
            CashFlowData.period_id == period_id
        ).scalar()
        
        return count > 0
    
    def _has_rent_roll_data(self, property_id: int, period_id: int) -> bool:
        """Check if rent roll data exists"""
        count = self.db.query(func.count(RentRollData.id)).filter(
            RentRollData.property_id == property_id,
            RentRollData.period_id == period_id
        ).scalar()
        
        return count > 0
    
    def _has_mortgage_data(self, property_id: int, period_id: int) -> bool:
        """Check if mortgage statement data exists (including fallback to earlier periods)"""
        # Check current period first
        count = self.db.query(func.count(MortgageStatementData.id)).filter(
            MortgageStatementData.property_id == property_id,
            MortgageStatementData.period_id == period_id
        ).scalar()

        if count > 0:
            return True

        # If no data for current period, check if ANY mortgage data exists for this property
        # (the calculate_mortgage_metrics method will use fallback logic to find latest)
        any_count = self.db.query(func.count(MortgageStatementData.id)).filter(
            MortgageStatementData.property_id == property_id
        ).scalar()

        return any_count > 0
    
    def _sum_balance_sheet_accounts_by_codes(
        self,
        property_id: int,
        period_id: int,
        account_codes: list
    ) -> Decimal:
        """
        Sum balance sheet accounts by specific account codes (Template v1.0 helper)
        
        Args:
            property_id: Property ID
            period_id: Period ID
            account_codes: List of specific account codes to sum
        
        Returns:
            Sum of specified accounts, or 0 if none found
        """
        if not account_codes:
            return Decimal('0')
        
        result = self.db.query(
            func.sum(BalanceSheetData.amount)
        ).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.period_id == period_id,
            BalanceSheetData.account_code.in_(account_codes),
            BalanceSheetData.is_calculated == False
        ).scalar()
        
        return result if result else Decimal('0')
    
    def _sum_balance_sheet_accounts_by_range(
        self,
        property_id: int,
        period_id: int,
        start_code: str,
        end_code: str
    ) -> Decimal:
        """
        Sum balance sheet accounts within a code range (Template v1.0 helper)
        
        Args:
            property_id: Property ID
            period_id: Period ID
            start_code: Starting account code (e.g., '0122')
            end_code: Ending account code (e.g., '0127')
        
        Returns:
            Sum of accounts in range, or 0 if none found
        
        Example:
            _sum_balance_sheet_accounts_by_range(1, 1, '0122', '0127')
            # Sums all accounts from 0122-xxxx to 0127-xxxx
        """
        # Query accounts where code starts with values in range
        result = self.db.query(
            func.sum(BalanceSheetData.amount)
        ).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.period_id == period_id,
            BalanceSheetData.account_code >= f"{start_code}-0000",
            BalanceSheetData.account_code <= f"{end_code}-9999",
            BalanceSheetData.is_calculated == False
        ).scalar()
        
        return result if result else Decimal('0')
    
    def _store_metrics(
        self, 
        property_id: int, 
        period_id: int, 
        metrics_data: Dict
    ) -> FinancialMetrics:
        """
        Store or update financial metrics
        
        Uses upsert logic:
        - If metrics exist for this property/period, update them
        - Otherwise, create new record
        """
        # Check if metrics already exist
        existing_metrics = self.db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == property_id,
            FinancialMetrics.period_id == period_id
        ).first()
        
        if existing_metrics:
            # Update existing metrics
            for key, value in metrics_data.items():
                if hasattr(existing_metrics, key):
                    # Handle 'PRESERVE' marker - keep existing value
                    if value == 'PRESERVE':
                        continue
                    setattr(existing_metrics, key, value)

            self.db.commit()
            self.db.refresh(existing_metrics)
            return existing_metrics
        else:
            # Create new metrics
            # Filter out 'PRESERVE' markers (they only apply to updates)
            clean_metrics_data = {k: v for k, v in metrics_data.items() if v != 'PRESERVE'}

            metrics = FinancialMetrics(
                property_id=property_id,
                period_id=period_id,
                **clean_metrics_data
            )

            self.db.add(metrics)
            self.db.commit()
            self.db.refresh(metrics)
            return metrics
