"""
Anomaly Detection Service for REIMS2
Statistical and ML-based anomaly detection for financial data.

Sprint 3: Alerts & Real-Time Anomaly Detection
"""
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import statistics
from decimal import Decimal

# ML-based anomaly detection
from pyod.models.iforest import IForest
from pyod.models.lof import LOF
import numpy as np

from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.financial_period import FinancialPeriod


class AnomalyDetectionService:
    """
    Detects anomalies in financial data using statistical and ML methods.
    
    Methods:
    - Z-score based detection
    - Percentage change detection
    - Missing data detection
    - ML-based outlier detection (Isolation Forest, LOF)
    """
    
    # Thresholds
    Z_SCORE_THRESHOLD = 3.0  # Standard deviations from mean
    PERCENTAGE_CHANGE_THRESHOLD = 50.0  # 50% change triggers alert
    
    def __init__(self, db: Session):
        """Initialize anomaly detection service."""
        self.db = db
    
    def detect_statistical_anomalies(
        self,
        property_id: int,
        table_name: str,
        lookback_months: int = 12
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalies using statistical methods (Z-score, percentage change).
        
        Args:
            property_id: Property to analyze
            table_name: Data table (balance_sheet_data, income_statement_data, etc.)
            lookback_months: Historical months to analyze
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        # Get historical data
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_months * 30)
        
        if table_name == 'balance_sheet':
            data = self.db.query(BalanceSheetData).join(
                FinancialPeriod
            ).filter(
                and_(
                    BalanceSheetData.property_id == property_id,
                    FinancialPeriod.period_end_date >= cutoff_date
                )
            ).order_by(FinancialPeriod.period_end_date).all()
        elif table_name == 'income_statement':
            data = self.db.query(IncomeStatementData).join(
                FinancialPeriod
            ).filter(
                and_(
                    IncomeStatementData.property_id == property_id,
                    FinancialPeriod.period_end_date >= cutoff_date
                )
            ).order_by(FinancialPeriod.period_end_date).all()
        else:
            return []
        
        if len(data) < 3:  # Need at least 3 data points
            return []
        
        # Analyze numeric fields
        numeric_fields = self._get_numeric_fields(table_name)
        
        for field in numeric_fields:
            values = []
            records = []
            
            for record in data:
                value = getattr(record, field, None)
                if value is not None and value != 0:
                    values.append(float(value))
                    records.append(record)
            
            if len(values) < 3:
                continue
            
            # Calculate statistics
            mean_val = statistics.mean(values)
            try:
                stdev = statistics.stdev(values)
            except statistics.StatisticsError:
                stdev = 0
            
            # Z-score anomaly detection
            if stdev > 0:
                for i, (value, record) in enumerate(zip(values, records)):
                    z_score = abs((value - mean_val) / stdev)
                    
                    if z_score > self.Z_SCORE_THRESHOLD:
                        anomalies.append({
                            'type': 'z_score',
                            'severity': 'high' if z_score > 4.0 else 'medium',
                            'record_id': record.id,
                            'field_name': field,
                            'value': value,
                            'z_score': round(z_score, 2),
                            'mean': round(mean_val, 2),
                            'stdev': round(stdev, 2),
                            'message': f'{field} value {value:,.2f} is {z_score:.1f} std deviations from mean ({mean_val:,.2f})'
                        })
            
            # Percentage change detection
            for i in range(1, len(values)):
                prev_value = values[i-1]
                curr_value = values[i]
                
                if prev_value != 0:
                    # Calculate percentage change preserving the sign (positive = increase, negative = decrease)
                    pct_change = (curr_value - prev_value) / prev_value * 100
                    pct_change_abs = abs(pct_change)
                    
                    # Check threshold using absolute value, but store the signed value
                    if pct_change_abs > self.PERCENTAGE_CHANGE_THRESHOLD:
                        anomalies.append({
                            'type': 'percentage_change',
                            'severity': 'high' if pct_change_abs > 100 else 'medium',
                            'record_id': records[i].id,
                            'field_name': field,
                            'value': curr_value,
                            'previous_value': prev_value,
                            'percentage_change': round(pct_change, 2),  # Preserve sign: positive for increase, negative for decrease
                            'message': f'{field} changed by {pct_change:+.1f}% from {prev_value:,.2f} to {curr_value:,.2f}'
                        })
        
        return anomalies
    
    def detect_ml_anomalies(
        self,
        property_id: int,
        table_name: str,
        method: str = 'iforest'
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalies using ML methods (Isolation Forest or LOF).
        
        Args:
            property_id: Property to analyze
            table_name: Data table
            method: 'iforest' or 'lof'
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        # Get historical data
        if table_name == 'balance_sheet':
            data = self.db.query(BalanceSheetData).filter(
                BalanceSheetData.property_id == property_id
            ).all()
        elif table_name == 'income_statement':
            data = self.db.query(IncomeStatementData).filter(
                IncomeStatementData.property_id == property_id
            ).all()
        else:
            return []
        
        if len(data) < 10:  # Need sufficient data for ML
            return []
        
        # Prepare feature matrix
        numeric_fields = self._get_numeric_fields(table_name)
        feature_matrix = []
        
        for record in data:
            features = []
            for field in numeric_fields:
                value = getattr(record, field, None)
                features.append(float(value) if value is not None else 0.0)
            feature_matrix.append(features)
        
        X = np.array(feature_matrix)
        
        # Train anomaly detector
        if method == 'iforest':
            detector = IForest(contamination=0.1, random_state=42)
        else:  # lof
            detector = LOF(contamination=0.1)
        
        detector.fit(X)
        predictions = detector.predict(X)  # 0 = normal, 1 = anomaly
        scores = detector.decision_scores_  # Anomaly scores
        
        # Identify anomalies
        for i, (record, is_anomaly, score) in enumerate(zip(data, predictions, scores)):
            if is_anomaly == 1:
                anomalies.append({
                    'type': f'ml_{method}',
                    'severity': 'high' if score > np.percentile(scores, 95) else 'medium',
                    'record_id': record.id,
                    'anomaly_score': round(float(score), 4),
                    'method': method.upper(),
                    'message': f'ML detected anomalous pattern in record {record.id} (score: {score:.2f})'
                })
        
        return anomalies
    
    def detect_missing_data(
        self,
        property_id: int,
        expected_periods: List[datetime]
    ) -> List[Dict[str, Any]]:
        """
        Detect missing financial periods.
        
        Args:
            property_id: Property ID
            expected_periods: List of expected period dates
            
        Returns:
            List of missing period anomalies
        """
        anomalies = []
        
        # Get actual periods
        actual_periods = self.db.query(FinancialPeriod).filter(
            FinancialPeriod.property_id == property_id
        ).all()
        
        actual_dates = set(p.period_end_date.date() for p in actual_periods)
        
        for expected_date in expected_periods:
            if expected_date.date() not in actual_dates:
                anomalies.append({
                    'type': 'missing_data',
                    'severity': 'high',
                    'period_date': expected_date.strftime('%Y-%m-%d'),
                    'message': f'Missing financial data for period {expected_date.strftime("%B %Y")}'
                })
        
        return anomalies
    
    def _get_numeric_fields(self, table_name: str) -> List[str]:
        """Get list of numeric fields for a given table."""
        if table_name == 'balance_sheet':
            return ['total_assets', 'total_liabilities', 'total_equity',
                   'current_assets', 'current_liabilities', 'net_assets']
        elif table_name == 'income_statement':
            return ['total_revenue', 'total_expenses', 'net_income',
                   'gross_profit', 'operating_income']
        return []

