"""
Cross-Validation Engine
Validates financial statement equations and multi-document consistency.
"""

from typing import Dict, Any, List
from decimal import Decimal


class CrossValidationEngine:
    """Comprehensive financial statement validation."""
    
    def validate_balance_sheet(
        self,
        assets: Decimal,
        liabilities: Decimal,
        equity: Decimal
    ) -> Dict[str, Any]:
        """Validate: Assets = Liabilities + Equity."""
        calculated = liabilities + equity
        difference = abs(assets - calculated)
        tolerance = assets * Decimal('0.01')
        
        return {
            "valid": difference <= tolerance,
            "equation": "Assets = Liabilities + Equity",
            "assets": float(assets),
            "liabilities_plus_equity": float(calculated),
            "difference": float(difference),
            "tolerance": float(tolerance)
        }
    
    def validate_income_statement(
        self,
        revenue: Decimal,
        operating_expenses: Decimal,
        net_income: Decimal,
        other_income: Decimal = Decimal('0'),
        taxes: Decimal = Decimal('0')
    ) -> Dict[str, Any]:
        """Validate income statement calculations."""
        calculated_net = revenue - operating_expenses + other_income - taxes
        difference = abs(net_income - calculated_net)
        tolerance = revenue * Decimal('0.02')
        
        return {
            "valid": difference <= tolerance,
            "calculated_net_income": float(calculated_net),
            "reported_net_income": float(net_income),
            "difference": float(difference)
        }
    
    def validate_cash_flow(
        self,
        beginning_cash: Decimal,
        cash_inflows: Decimal,
        cash_outflows: Decimal,
        ending_cash: Decimal
    ) -> Dict[str, Any]:
        """Validate cash flow reconciliation."""
        calculated_ending = beginning_cash + cash_inflows - cash_outflows
        difference = abs(ending_cash - calculated_ending)
        
        return {
            "valid": difference < Decimal('1.00'),  # $1 tolerance
            "calculated_ending_cash": float(calculated_ending),
            "reported_ending_cash": float(ending_cash),
            "difference": float(difference)
        }

