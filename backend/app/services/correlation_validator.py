"""
Cross-Field Correlation Validator
Validates relationships between financial fields.
"""

from typing import Dict, Any, List
from decimal import Decimal


class CorrelationValidator:
    """Validate correlations between financial fields."""
    
    def validate_revenue_expenses(
        self,
        revenue: Decimal,
        expenses: Decimal
    ) -> Dict[str, Any]:
        """Validate revenue vs expenses ratio."""
        if revenue == 0:
            return {"valid": False, "reason": "Zero revenue"}
        
        ratio = expenses / revenue
        valid = Decimal('0.3') <= ratio <= Decimal('0.8')
        
        return {
            "valid": valid,
            "ratio": float(ratio),
            "expected_range": "30-80%"
        }
    
    def validate_assets_liabilities(
        self,
        assets: Decimal,
        liabilities: Decimal,
        equity: Decimal
    ) -> Dict[str, Any]:
        """Validate balance sheet equation."""
        calculated_equity = assets - liabilities
        difference = abs(equity - calculated_equity)
        tolerance = assets * Decimal('0.01')  # 1% tolerance
        
        return {
            "valid": difference <= tolerance,
            "calculated_equity": float(calculated_equity),
            "reported_equity": float(equity),
            "difference": float(difference)
        }
    
    def validate_occupancy_rental_income(
        self,
        occupancy_rate: Decimal,
        rental_income: Decimal,
        total_units: int,
        avg_rent: Decimal
    ) -> Dict[str, Any]:
        """Validate occupancy vs rental income consistency."""
        expected_income = total_units * occupancy_rate * avg_rent
        difference_pct = abs(rental_income - expected_income) / expected_income if expected_income > 0 else Decimal('1.0')
        
        return {
            "valid": difference_pct < Decimal('0.15'),  # 15% tolerance
            "expected_income": float(expected_income),
            "actual_income": float(rental_income),
            "variance_pct": float(difference_pct * 100)
        }

