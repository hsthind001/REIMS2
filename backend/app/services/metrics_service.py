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
from app.models.financial_metrics import FinancialMetrics


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
        
        # Cash Flow Metrics (if data exists)
        if self._has_cash_flow_data(property_id, period_id):
            metrics_data.update(self.calculate_cash_flow_metrics(property_id, period_id))
        
        # Rent Roll Metrics (if data exists)
        if self._has_rent_roll_data(property_id, period_id):
            metrics_data.update(self.calculate_rent_roll_metrics(property_id, period_id))
        
        # Performance Metrics (requires both IS and RR data)
        if self._has_income_statement_data(property_id, period_id) and self._has_rent_roll_data(property_id, period_id):
            metrics_data.update(self.calculate_performance_metrics(property_id, period_id, metrics_data))
        
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
        - LTV Ratio: Total Long-Term Debt / Net Property Value
        """
        total_assets = totals.get("total_assets") or Decimal('0')
        total_liabilities = totals.get("total_liabilities") or Decimal('0')
        total_equity = totals.get("total_equity") or Decimal('0')
        long_term_debt = totals.get("total_long_term_liabilities") or Decimal('0')
        net_property_value = totals.get("total_property_equipment") or Decimal('0')
        
        return {
            "debt_to_assets_ratio": self.safe_divide(total_liabilities, total_assets),
            "debt_to_equity_ratio": self.safe_divide(total_liabilities, total_equity),
            "equity_ratio": self.safe_divide(total_equity, total_assets),
            "ltv_ratio": self.safe_divide(long_term_debt, net_property_value),
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
        noi = self._get_income_statement_total(property_id, period_id, '6299-0000')
        net_income = self._get_income_statement_total(property_id, period_id, '9090-0000')
        
        # If totals not found, sum categories
        if not total_revenue:
            total_revenue = self._sum_income_statement_accounts(
                property_id, period_id, account_pattern='4%', is_calculated=False
            )
        
        if not total_expenses:
            total_expenses = self._sum_income_statement_accounts(
                property_id, period_id, account_pattern='[5-8]%', is_calculated=False
            )
        
        # Calculate margins
        operating_margin = self.safe_divide(noi, total_revenue) * Decimal('100')
        profit_margin = self.safe_divide(net_income, total_revenue) * Decimal('100')
        
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
        expense_ratio = self.safe_divide(expenses, revenue) * Decimal('100')
        
        return {
            "noi_per_sqft": noi_per_sqft,
            "revenue_per_sqft": revenue_per_sqft,
            "expense_ratio": expense_ratio,
        }
    
    # ==================== HELPER METHODS ====================
    
    def calculate_rent_roll_stats(
        self, 
        property_id: int, 
        period_id: int
    ) -> Dict:
        """
        Aggregate rent roll statistics
        
        Returns detailed statistics from rent roll data
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
        
        # Count units
        total_units = len(rent_roll)
        occupied_units = sum(1 for unit in rent_roll if unit.occupancy_status == 'occupied')
        vacant_units = total_units - occupied_units
        
        # Sum sqft
        total_leasable_sqft = sum(
            unit.unit_area_sqft for unit in rent_roll 
            if unit.unit_area_sqft is not None
        )
        occupied_sqft = sum(
            unit.unit_area_sqft for unit in rent_roll 
            if unit.unit_area_sqft is not None and unit.occupancy_status == 'occupied'
        )
        
        # Sum rents
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
    
    def _sum_income_statement_accounts(
        self, 
        property_id: int, 
        period_id: int, 
        account_pattern: str,
        is_calculated: bool = False
    ) -> Optional[Decimal]:
        """Sum income statement accounts matching pattern"""
        result = self.db.query(
            func.sum(IncomeStatementData.period_amount)
        ).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code.like(account_pattern),
            IncomeStatementData.is_calculated == is_calculated
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
                    setattr(existing_metrics, key, value)
            
            self.db.commit()
            self.db.refresh(existing_metrics)
            return existing_metrics
        else:
            # Create new metrics
            metrics = FinancialMetrics(
                property_id=property_id,
                period_id=period_id,
                **metrics_data
            )
            
            self.db.add(metrics)
            self.db.commit()
            self.db.refresh(metrics)
            return metrics

