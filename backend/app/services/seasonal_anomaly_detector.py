"""
Seasonal Anomaly Detector Service

Implements finance-aware seasonal baseline detection using:
- STL (Seasonal-Trend Decomposition) for seasonal decomposition
- Year-over-year (YoY) comparisons
- Rolling 3-year month-of-year average
- Seasonal index adjustments

Integrates with AnomalyDetectionService to set baseline_type='seasonal' in anomaly records.
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
import numpy as np
import pandas as pd
import logging

from app.models.anomaly_detection import AnomalyDetection, BaselineType
from app.models.income_statement_data import IncomeStatementData
from app.models.balance_sheet_data import BalanceSheetData
from app.models.financial_period import FinancialPeriod
from app.models.property import Property
from app.services.seasonal_analyzer import SeasonalAnalyzer

logger = logging.getLogger(__name__)


class SeasonalAnomalyDetector:
    """
    Detects anomalies using seasonal baselines instead of simple mean-based baselines.
    
    This is finance-aware detection that accounts for:
    - Seasonal patterns (e.g., rent/expenses often have seasonality)
    - Year-over-year comparisons
    - Month-of-year patterns
    - Rolling multi-year averages
    """
    
    def __init__(self, db: Session):
        """Initialize seasonal anomaly detector."""
        self.db = db
        self.seasonal_analyzer = SeasonalAnalyzer()
        self.z_score_threshold = 2.5  # Threshold for seasonal-adjusted anomalies
    
    def detect_seasonal_anomalies(
        self,
        property_id: int,
        account_code: str,
        document_type: str = 'income_statement',
        lookback_years: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalies using seasonal baseline detection.
        
        Args:
            property_id: Property to analyze
            account_code: Account code to analyze
            document_type: Type of document (income_statement, balance_sheet)
            lookback_years: Number of years of historical data to use (default: 3)
            
        Returns:
            List of detected anomalies with seasonal baseline information
        """
        anomalies = []
        
        # Get historical data
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_years * 365)
        
        if document_type == 'income_statement':
            data = self._get_income_statement_data(property_id, account_code, cutoff_date)
        elif document_type == 'balance_sheet':
            data = self._get_balance_sheet_data(property_id, account_code, cutoff_date)
        else:
            logger.warning(f"Unsupported document type: {document_type}")
            return []
        
        if len(data) < 12:  # Need at least 12 months for seasonality
            logger.info(f"Insufficient data for seasonal analysis: {len(data)} periods")
            return []
        
        # Extract values and dates
        values = [float(item['amount']) for item in data]
        dates = [item['period_end_date'] for item in data]
        
        # Calculate seasonal expected values using multiple methods
        current_period = data[-1]
        current_date = current_period['period_end_date']
        current_value = float(current_period['amount'])
        
        # Method 1: Year-over-Year (YoY) comparison
        yoy_expected = self._calculate_yoy_expected(data, current_date)
        
        # Method 2: Rolling 3-year month-of-year average
        rolling_expected = self._calculate_rolling_month_average(data, current_date, years=3)
        
        # Method 3: Seasonal index adjustment (using STL decomposition)
        seasonal_expected = self._calculate_seasonal_index_expected(values, dates, current_date)
        
        # Use the most appropriate expected value (prefer seasonal if available)
        if seasonal_expected['confidence'] > 0.7:
            expected_value = seasonal_expected['expected_value']
            baseline_method = 'seasonal_stl'
        elif rolling_expected['confidence'] > 0.6:
            expected_value = rolling_expected['expected_value']
            baseline_method = 'rolling_3yr_month'
        else:
            expected_value = yoy_expected['expected_value']
            baseline_method = 'yoy'
        
        # Calculate deviation
        deviation = current_value - expected_value
        deviation_pct = (deviation / expected_value * 100) if expected_value != 0 else 0
        
        # Calculate Z-score using seasonal-adjusted residuals
        residuals = [v - exp for v, exp in zip(values[:-1], [expected_value] * (len(values) - 1))]
        if len(residuals) > 2:
            residual_mean = np.mean(residuals)
            residual_std = np.std(residuals) if len(residuals) > 1 else 1.0
            if residual_std > 0:
                z_score = (current_value - expected_value) / residual_std
            else:
                z_score = 0.0
        else:
            z_score = abs(deviation_pct) / 20.0  # Rough approximation
        
        # Determine severity
        if abs(z_score) >= 3.0 or abs(deviation_pct) >= 50:
            severity = 'critical'
        elif abs(z_score) >= 2.5 or abs(deviation_pct) >= 30:
            severity = 'high'
        elif abs(z_score) >= 2.0 or abs(deviation_pct) >= 20:
            severity = 'medium'
        else:
            severity = 'low'
        
        # Only flag if exceeds threshold
        if abs(z_score) >= self.z_score_threshold or abs(deviation_pct) >= 20:
            anomaly = {
                'type': 'seasonal_anomaly',
                'severity': severity,
                'property_id': property_id,
                'account_code': account_code,
                'document_type': document_type,
                'current_value': current_value,
                'expected_value': expected_value,
                'deviation': deviation,
                'deviation_percentage': deviation_pct,
                'z_score': z_score,
                'baseline_type': 'seasonal',
                'baseline_method': baseline_method,
                'yoy_expected': yoy_expected['expected_value'],
                'rolling_expected': rolling_expected['expected_value'],
                'seasonal_expected': seasonal_expected['expected_value'],
                'seasonal_component': seasonal_expected.get('seasonal_component', 0.0),
                'trend_component': seasonal_expected.get('trend_value', expected_value),
                'confidence': max(
                    seasonal_expected.get('confidence', 0.5),
                    rolling_expected.get('confidence', 0.5),
                    yoy_expected.get('confidence', 0.5)
                ),
                'period_id': current_period['period_id'],
                'document_id': current_period.get('document_id'),
                'detected_at': datetime.utcnow()
            }
            anomalies.append(anomaly)
        
        return anomalies
    
    def _get_income_statement_data(
        self,
        property_id: int,
        account_code: str,
        cutoff_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get income statement data for seasonal analysis."""
        data = self.db.query(
            IncomeStatementData.period_amount,
            FinancialPeriod.period_end_date,
            FinancialPeriod.id.label('period_id'),
            IncomeStatementData.upload_id.label('document_id')
        ).join(
            FinancialPeriod, IncomeStatementData.period_id == FinancialPeriod.id
        ).filter(
            and_(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.account_code == account_code,
                FinancialPeriod.period_end_date >= cutoff_date
            )
        ).order_by(FinancialPeriod.period_end_date).all()
        
        return [
            {
                'amount': float(row.period_amount or 0),
                'period_end_date': row.period_end_date,
                'period_id': row.period_id,
                'document_id': row.document_id
            }
            for row in data
        ]
    
    def _get_balance_sheet_data(
        self,
        property_id: int,
        account_code: str,
        cutoff_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get balance sheet data for seasonal analysis."""
        data = self.db.query(
            BalanceSheetData.amount,
            FinancialPeriod.period_end_date,
            FinancialPeriod.id.label('period_id'),
            BalanceSheetData.upload_id.label('document_id')
        ).join(
            FinancialPeriod, BalanceSheetData.period_id == FinancialPeriod.id
        ).filter(
            and_(
                BalanceSheetData.property_id == property_id,
                BalanceSheetData.account_code == account_code,
                FinancialPeriod.period_end_date >= cutoff_date
            )
        ).order_by(FinancialPeriod.period_end_date).all()
        
        return [
            {
                'amount': float(row.amount or 0),
                'period_end_date': row.period_end_date,
                'period_id': row.period_id,
                'document_id': row.document_id
            }
            for row in data
        ]
    
    def _calculate_yoy_expected(
        self,
        data: List[Dict[str, Any]],
        target_date: datetime
    ) -> Dict[str, Any]:
        """
        Calculate expected value using year-over-year comparison.
        
        Same month last year (YoY).
        """
        target_month = target_date.month
        target_year = target_date.year
        
        # Find same month in previous years
        yoy_values = []
        for item in data:
            period_date = item['period_end_date']
            if period_date.month == target_month and period_date.year < target_year:
                yoy_values.append(item['amount'])
        
        if yoy_values:
            expected = np.mean(yoy_values)
            confidence = min(0.9, 0.5 + len(yoy_values) * 0.1)
        else:
            # Fallback to overall mean
            expected = np.mean([item['amount'] for item in data])
            confidence = 0.5
        
        return {
            'expected_value': float(expected),
            'confidence': confidence,
            'method': 'yoy'
        }
    
    def _calculate_rolling_month_average(
        self,
        data: List[Dict[str, Any]],
        target_date: datetime,
        years: int = 3
    ) -> Dict[str, Any]:
        """
        Calculate expected value using rolling N-year month-of-year average.
        
        Example: For December 2024, average all December values from 2021-2023.
        """
        target_month = target_date.month
        cutoff_year = target_date.year - years
        
        # Get all values for the same month across the rolling window
        month_values = []
        for item in data:
            period_date = item['period_end_date']
            if period_date.month == target_month and cutoff_year <= period_date.year < target_date.year:
                month_values.append(item['amount'])
        
        if month_values:
            expected = np.mean(month_values)
            confidence = min(0.95, 0.6 + len(month_values) * 0.05)
        else:
            # Fallback to overall mean
            expected = np.mean([item['amount'] for item in data])
            confidence = 0.5
        
        return {
            'expected_value': float(expected),
            'confidence': confidence,
            'method': f'rolling_{years}yr_month'
        }
    
    def _calculate_seasonal_index_expected(
        self,
        values: List[float],
        dates: List[datetime],
        target_date: datetime
    ) -> Dict[str, Any]:
        """
        Calculate expected value using seasonal index adjustment from STL decomposition.
        
        Uses the SeasonalAnalyzer to get trend + seasonal components.
        """
        try:
            result = self.seasonal_analyzer.calculate_seasonal_expected_value(
                values=values,
                dates=dates,
                target_date=target_date,
                use_seasonality=True
            )
            
            return {
                'expected_value': result['expected_value'],
                'trend_value': result['trend_value'],
                'seasonal_component': result['seasonal_component'],
                'confidence': result['confidence'],
                'method': result.get('decomposition_method', 'stl')
            }
        except Exception as e:
            logger.warning(f"Seasonal index calculation failed: {e}, using fallback")
            # Fallback to simple mean
            return {
                'expected_value': float(np.mean(values)),
                'trend_value': float(np.mean(values)),
                'seasonal_component': 0.0,
                'confidence': 0.5,
                'method': 'fallback_mean'
            }
    
    def save_anomaly_to_db(
        self,
        anomaly: Dict[str, Any],
        document_id: int
    ) -> Optional[AnomalyDetection]:
        """
        Save seasonal anomaly to database with baseline_type='seasonal'.
        
        Args:
            anomaly: Anomaly dictionary from detect_seasonal_anomalies
            document_id: Document ID to associate with
            
        Returns:
            Created AnomalyDetection record
        """
        try:
            anomaly_record = AnomalyDetection(
                document_id=document_id,
                field_name=anomaly['account_code'],
                field_value=str(anomaly['current_value']),
                expected_value=str(anomaly['expected_value']),
                z_score=Decimal(str(anomaly['z_score'])),
                percentage_change=Decimal(str(anomaly['deviation_percentage'])),
                anomaly_type='seasonal',
                severity=anomaly['severity'],
                confidence=Decimal(str(anomaly['confidence'])),
                baseline_type=BaselineType.SEASONAL,  # Set baseline_type='seasonal'
                direction='up' if anomaly['deviation'] > 0 else 'down',
                anomaly_category='performance',  # Could be enhanced based on account type
                pattern_type='seasonality',
                metadata_json={
                    'baseline_method': anomaly.get('baseline_method', 'seasonal_stl'),
                    'yoy_expected': anomaly.get('yoy_expected'),
                    'rolling_expected': anomaly.get('rolling_expected'),
                    'seasonal_expected': anomaly.get('seasonal_expected'),
                    'seasonal_component': anomaly.get('seasonal_component'),
                    'trend_component': anomaly.get('trend_component'),
                }
            )
            
            self.db.add(anomaly_record)
            self.db.commit()
            self.db.refresh(anomaly_record)
            
            logger.info(f"Saved seasonal anomaly: {anomaly_record.id} for account {anomaly['account_code']}")
            return anomaly_record
            
        except Exception as e:
            logger.error(f"Error saving seasonal anomaly: {e}")
            self.db.rollback()
            return None
