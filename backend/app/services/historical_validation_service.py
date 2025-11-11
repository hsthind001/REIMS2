"""
Historical Validation Service for REIMS2
Validates current data against historical baselines and trends.

Sprint 4: Multi-Layer Statistical Validation
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
import statistics
from decimal import Decimal

from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.financial_period import FinancialPeriod


class HistoricalValidationService:
    """
    Validates financial data against historical baselines.
    
    Features:
    - 12-24 month historical analysis
    - Statistical baselines (mean, median, percentiles)
    - Seasonal pattern detection
    - Trend analysis
    """
    
    def __init__(self, db: Session):
        """Initialize historical validation service."""
        self.db = db
    
    def calculate_baselines(
        self,
        property_id: int,
        table_name: str,
        lookback_months: int = 12
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate statistical baselines for all numeric fields.
        
        Args:
            property_id: Property ID
            table_name: Data table
            lookback_months: Months of history to analyze
            
        Returns:
            Dict mapping field_name -> {mean, median, p25, p75, min, max}
        """
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_months * 30)
        
        if table_name == 'balance_sheet':
            model = BalanceSheetData
        elif table_name == 'income_statement':
            model = IncomeStatementData
        else:
            return {}
        
        data = self.db.query(model).join(FinancialPeriod).filter(
            and_(
                model.property_id == property_id,
                FinancialPeriod.period_end_date >= cutoff_date
            )
        ).all()
        
        if not data:
            return {}
        
        numeric_fields = self._get_numeric_fields(table_name)
        baselines = {}
        
        for field in numeric_fields:
            values = [float(getattr(r, field, 0) or 0) for r in data]
            values = [v for v in values if v != 0]  # Exclude zeros
            
            if values:
                baselines[field] = {
                    'mean': round(statistics.mean(values), 2),
                    'median': round(statistics.median(values), 2),
                    'min': round(min(values), 2),
                    'max': round(max(values), 2),
                    'p25': round(statistics.quantiles(values, n=4)[0], 2) if len(values) >= 4 else 0,
                    'p75': round(statistics.quantiles(values, n=4)[2], 2) if len(values) >= 4 else 0,
                    'sample_count': len(values)
                }
        
        return baselines
    
    def validate_against_baseline(
        self,
        property_id: int,
        table_name: str,
        current_data: Dict[str, float],
        tolerance_percentage: float = 25.0
    ) -> List[Dict[str, Any]]:
        """
        Validate current data against historical baselines.
        
        Args:
            property_id: Property ID
            table_name: Data table
            current_data: Current field values
            tolerance_percentage: Acceptable deviation percentage
            
        Returns:
            List of validation issues
        """
        baselines = self.calculate_baselines(property_id, table_name)
        issues = []
        
        for field, value in current_data.items():
            if field not in baselines:
                continue
            
            baseline = baselines[field]
            mean = baseline['mean']
            
            if mean == 0:
                continue
            
            deviation = abs(value - mean) / mean * 100
            
            if deviation > tolerance_percentage:
                issues.append({
                    'field': field,
                    'current_value': value,
                    'historical_mean': mean,
                    'deviation_percentage': round(deviation, 2),
                    'severity': 'high' if deviation > 50 else 'medium',
                    'message': f'{field} deviates {deviation:.1f}% from historical mean'
                })
        
        return issues
    
    def _get_numeric_fields(self, table_name: str) -> List[str]:
        """Get numeric field names for a table."""
        if table_name == 'balance_sheet':
            return ['total_assets', 'total_liabilities', 'total_equity']
        elif table_name == 'income_statement':
            return ['total_revenue', 'total_expenses', 'net_income']
        return []

