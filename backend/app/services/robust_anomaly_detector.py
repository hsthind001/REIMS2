"""
Robust Anomaly Detector Service

Implements robust statistics using Median Absolute Deviation (MAD) instead of mean/std.
More resilient to outliers in historical data.

Robust Z-score = (value - median) / MAD
where MAD = median(|x_i - median(x)|)

This is more robust than standard Z-score when historical data contains outliers.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import numpy as np
from scipy.stats import median_abs_deviation
import logging

from app.models.anomaly_detection import AnomalyDetection, BaselineType
from app.models.income_statement_data import IncomeStatementData
from app.models.balance_sheet_data import BalanceSheetData
from app.models.financial_period import FinancialPeriod

logger = logging.getLogger(__name__)


class RobustAnomalyDetector:
    """
    Detects anomalies using robust statistics (Median/MAD) instead of mean/std.
    
    Advantages:
    - More resilient to outliers in historical data
    - Better handles fat-tailed distributions
    - Less sensitive to single large anomalies in training data
    """
    
    def __init__(self, db: Session):
        """Initialize robust anomaly detector."""
        self.db = db
        self.robust_z_score_threshold = 2.5  # Threshold for robust Z-score
    
    def detect_robust_anomalies(
        self,
        property_id: int,
        account_code: str,
        document_type: str = 'income_statement',
        lookback_periods: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalies using robust statistics (Median/MAD).
        
        Args:
            property_id: Property to analyze
            account_code: Account code to analyze
            document_type: Type of document (income_statement, balance_sheet)
            lookback_periods: Number of historical periods to use
            
        Returns:
            List of detected anomalies with robust statistics
        """
        anomalies = []
        
        # Get historical data
        if document_type == 'income_statement':
            data = self._get_income_statement_data(property_id, account_code, lookback_periods)
        elif document_type == 'balance_sheet':
            data = self._get_balance_sheet_data(property_id, account_code, lookback_periods)
        else:
            logger.warning(f"Unsupported document type: {document_type}")
            return []
        
        if len(data) < 6:  # Need at least 6 periods for robust stats
            logger.info(f"Insufficient data for robust analysis: {len(data)} periods")
            return []
        
        # Extract values
        values = np.array([float(item['amount']) for item in data])
        
        # Calculate robust statistics
        median = np.median(values)
        mad = median_abs_deviation(values, scale=1.0)  # Use scale=1.0 for consistency factor
        
        if mad == 0:
            # All values are the same - no anomaly possible
            return []
        
        # Get current period
        current_period = data[-1]
        current_value = float(current_period['amount'])
        
        # Calculate robust Z-score
        robust_z_score = (current_value - median) / mad
        
        # Calculate deviation
        deviation = current_value - median
        deviation_pct = (deviation / median * 100) if median != 0 else 0
        
        # Compare with standard Z-score for reference
        mean = np.mean(values)
        std = np.std(values) if len(values) > 1 else 1.0
        standard_z_score = (current_value - mean) / std if std > 0 else 0.0
        
        # Determine severity
        if abs(robust_z_score) >= 3.0 or abs(deviation_pct) >= 50:
            severity = 'critical'
        elif abs(robust_z_score) >= 2.5 or abs(deviation_pct) >= 30:
            severity = 'high'
        elif abs(robust_z_score) >= 2.0 or abs(deviation_pct) >= 20:
            severity = 'medium'
        else:
            severity = 'low'
        
        # Only flag if exceeds threshold
        if abs(robust_z_score) >= self.robust_z_score_threshold or abs(deviation_pct) >= 20:
            anomaly = {
                'type': 'robust_anomaly',
                'severity': severity,
                'property_id': property_id,
                'account_code': account_code,
                'document_type': document_type,
                'current_value': current_value,
                'expected_value': median,  # Use median as expected value
                'deviation': deviation,
                'deviation_percentage': deviation_pct,
                'robust_z_score': robust_z_score,
                'standard_z_score': standard_z_score,  # For comparison
                'median': median,
                'mad': mad,
                'mean': mean,  # For reference
                'std': std,  # For reference
                'baseline_type': 'mean',  # Still using mean baseline, but robust detection
                'detection_method': 'robust_mad',
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
        lookback_periods: int
    ) -> List[Dict[str, Any]]:
        """Get income statement data for robust analysis."""
        data = self.db.query(
            IncomeStatementData.period_amount,
            FinancialPeriod.period_end_date,
            FinancialPeriod.id.label('period_id'),
            IncomeStatementData.upload_id.label('document_id')
        ).join(
            FinancialPeriod, IncomeStatementData.period_id == FinancialPeriod.id
        ).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.account_code == account_code
        ).order_by(FinancialPeriod.period_end_date).limit(lookback_periods + 1).all()
        
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
        lookback_periods: int
    ) -> List[Dict[str, Any]]:
        """Get balance sheet data for robust analysis."""
        data = self.db.query(
            BalanceSheetData.amount,
            FinancialPeriod.period_end_date,
            FinancialPeriod.id.label('period_id'),
            BalanceSheetData.upload_id.label('document_id')
        ).join(
            FinancialPeriod, BalanceSheetData.period_id == FinancialPeriod.id
        ).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.account_code == account_code
        ).order_by(FinancialPeriod.period_end_date).limit(lookback_periods + 1).all()
        
        return [
            {
                'amount': float(row.amount or 0),
                'period_end_date': row.period_end_date,
                'period_id': row.period_id,
                'document_id': row.document_id
            }
            for row in data
        ]
    
    def save_anomaly_to_db(
        self,
        anomaly: Dict[str, Any],
        document_id: int
    ) -> Optional[AnomalyDetection]:
        """
        Save robust anomaly to database.
        
        Args:
            anomaly: Anomaly dictionary from detect_robust_anomalies
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
                z_score=Decimal(str(anomaly['robust_z_score'])),
                percentage_change=Decimal(str(anomaly['deviation_percentage'])),
                anomaly_type='robust_statistical',
                severity=anomaly['severity'],
                confidence=Decimal('0.85'),  # Robust methods generally have good confidence
                baseline_type=BaselineType.MEAN,  # Baseline is still mean-based, but detection is robust
                direction='up' if anomaly['deviation'] > 0 else 'down',
                anomaly_category='performance',
                pattern_type='point',
                metadata_json={
                    'detection_method': 'robust_mad',
                    'robust_z_score': anomaly.get('robust_z_score'),
                    'standard_z_score': anomaly.get('standard_z_score'),
                    'median': anomaly.get('median'),
                    'mad': anomaly.get('mad'),
                    'mean': anomaly.get('mean'),
                    'std': anomaly.get('std'),
                }
            )
            
            self.db.add(anomaly_record)
            self.db.commit()
            self.db.refresh(anomaly_record)
            
            logger.info(f"Saved robust anomaly: {anomaly_record.id} for account {anomaly['account_code']}")
            return anomaly_record
            
        except Exception as e:
            logger.error(f"Error saving robust anomaly: {e}")
            self.db.rollback()
            return None
