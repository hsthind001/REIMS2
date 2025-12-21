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
from pyod.models.ocsvm import OCSVM
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Optional deep learning imports
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available - Autoencoder and LSTM models disabled")

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
    - ML-based outlier detection (Isolation Forest, LOF, One-Class SVM)
    - Deep learning (Autoencoder, LSTM) - requires PyTorch
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
        method: str = 'iforest',
        feature_matrix: Optional[np.ndarray] = None,
        records: Optional[List] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalies using ML methods.
        
        Supported methods:
        - 'iforest': Isolation Forest
        - 'lof': Local Outlier Factor
        - 'ocsvm': One-Class SVM
        - 'autoencoder': Deep learning autoencoder (requires PyTorch, 24+ months data)
        - 'lstm': LSTM time series anomaly detection (requires PyTorch, 24+ months data)
        
        Args:
            property_id: Property to analyze
            table_name: Data table
            method: ML method to use
            feature_matrix: Optional pre-computed feature matrix
            records: Optional list of records corresponding to feature_matrix
        
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        # Get data if not provided
        if feature_matrix is None or records is None:
            if table_name == 'balance_sheet':
                data = self.db.query(BalanceSheetData).filter(
                    BalanceSheetData.property_id == property_id
                ).order_by(BalanceSheetData.id).all()
            elif table_name == 'income_statement':
                data = self.db.query(IncomeStatementData).filter(
                    IncomeStatementData.property_id == property_id
                ).order_by(IncomeStatementData.id).all()
            else:
                return []
            
            if len(data) < 10:  # Need sufficient data for ML
                return []
            
            # Prepare feature matrix
            numeric_fields = self._get_numeric_fields(table_name)
            feature_matrix = []
            records = []
            
            for record in data:
                features = []
                for field in numeric_fields:
                    value = getattr(record, field, None)
                    features.append(float(value) if value is not None else 0.0)
                feature_matrix.append(features)
                records.append(record)
        
        X = np.array(feature_matrix)
        
        # Minimum data requirements
        min_data = {
            'iforest': 10,
            'lof': 10,
            'ocsvm': 10,
            'autoencoder': 24,
            'lstm': 24
        }
        
        if len(X) < min_data.get(method, 10):
            logger.warning(f"Insufficient data for {method}: need {min_data.get(method, 10)}, have {len(X)}")
            return []
        
        # Train anomaly detector based on method
        try:
            if method == 'iforest':
                detector = IForest(contamination=0.1, random_state=42)
                detector.fit(X)
                predictions = detector.predict(X)
                scores = detector.decision_scores_
            
            elif method == 'lof':
                detector = LOF(contamination=0.1)
                detector.fit(X)
                predictions = detector.predict(X)
                scores = detector.decision_scores_
            
            elif method == 'ocsvm':
                detector = OCSVM(contamination=0.1, kernel='rbf')
                detector.fit(X)
                predictions = detector.predict(X)
                scores = detector.decision_scores_
            
            elif method == 'autoencoder':
                if not TORCH_AVAILABLE:
                    logger.warning("PyTorch not available for autoencoder")
                    return []
                predictions, scores = self._detect_with_autoencoder(X)
            
            elif method == 'lstm':
                if not TORCH_AVAILABLE:
                    logger.warning("PyTorch not available for LSTM")
                    return []
                predictions, scores = self._detect_with_lstm(X)
            
            else:
                logger.warning(f"Unknown ML method: {method}")
                return []
            
            # Identify anomalies
            for i, (record, is_anomaly, score) in enumerate(zip(records, predictions, scores)):
                if is_anomaly == 1:
                    anomalies.append({
                        'type': f'ml_{method}',
                        'severity': 'high' if score > np.percentile(scores, 95) else 'medium',
                        'record_id': record.id,
                        'anomaly_score': round(float(score), 4),
                        'method': method.upper(),
                        'message': f'ML ({method}) detected anomalous pattern in record {record.id} (score: {score:.2f})'
                    })
        
        except Exception as e:
            logger.error(f"Error in ML anomaly detection ({method}): {e}")
            return []
        
        return anomalies
    
    def _detect_with_autoencoder(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect anomalies using autoencoder.
        
        Args:
            X: Feature matrix
        
        Returns:
            (predictions, scores) tuple
        """
        if not TORCH_AVAILABLE:
            return np.zeros(len(X)), np.zeros(len(X))
        
        try:
            # Simple autoencoder architecture
            class Autoencoder(nn.Module):
                def __init__(self, input_dim, encoding_dim=8):
                    super(Autoencoder, self).__init__()
                    self.encoder = nn.Sequential(
                        nn.Linear(input_dim, encoding_dim * 2),
                        nn.ReLU(),
                        nn.Linear(encoding_dim * 2, encoding_dim)
                    )
                    self.decoder = nn.Sequential(
                        nn.Linear(encoding_dim, encoding_dim * 2),
                        nn.ReLU(),
                        nn.Linear(encoding_dim * 2, input_dim)
                    )
                
                def forward(self, x):
                    encoded = self.encoder(x)
                    decoded = self.decoder(encoded)
                    return decoded
            
            # Normalize data
            X_mean = np.mean(X, axis=0)
            X_std = np.std(X, axis=0) + 1e-8
            X_norm = (X - X_mean) / X_std
            
            # Convert to tensor
            X_tensor = torch.FloatTensor(X_norm)
            
            # Initialize model
            input_dim = X.shape[1]
            encoding_dim = max(4, input_dim // 4)
            model = Autoencoder(input_dim, encoding_dim)
            
            # Train (simplified - in production, use proper training loop)
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
            criterion = nn.MSELoss()
            
            # Quick training (10 epochs)
            model.train()
            for epoch in range(10):
                optimizer.zero_grad()
                reconstructed = model(X_tensor)
                loss = criterion(reconstructed, X_tensor)
                loss.backward()
                optimizer.step()
            
            # Calculate reconstruction errors
            model.eval()
            with torch.no_grad():
                reconstructed = model(X_tensor)
                reconstruction_errors = torch.mean((X_tensor - reconstructed) ** 2, dim=1).numpy()
            
            # Threshold based on reconstruction error
            threshold = np.percentile(reconstruction_errors, 90)  # Top 10% are anomalies
            predictions = (reconstruction_errors > threshold).astype(int)
            scores = reconstruction_errors
            
            return predictions, scores
        
        except Exception as e:
            logger.error(f"Autoencoder detection error: {e}")
            return np.zeros(len(X)), np.zeros(len(X))
    
    def _detect_with_lstm(self, X: np.ndarray, sequence_length: int = 12) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect anomalies using LSTM for time series.
        
        Args:
            X: Feature matrix (time series)
            sequence_length: Length of input sequences
        
        Returns:
            (predictions, scores) tuple
        """
        if not TORCH_AVAILABLE or len(X) < sequence_length * 2:
            return np.zeros(len(X)), np.zeros(len(X))
        
        try:
            class LSTMAutoencoder(nn.Module):
                def __init__(self, input_dim, hidden_dim=32, num_layers=2):
                    super(LSTMAutoencoder, self).__init__()
                    self.hidden_dim = hidden_dim
                    self.num_layers = num_layers
                    
                    # Encoder
                    self.encoder = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)
                    # Decoder
                    self.decoder = nn.LSTM(hidden_dim, input_dim, num_layers, batch_first=True)
                
                def forward(self, x):
                    # Encode
                    encoded, (hidden, cell) = self.encoder(x)
                    # Decode (use last hidden state)
                    decoded, _ = self.decoder(encoded, (hidden, cell))
                    return decoded
            
            # Create sequences
            sequences = []
            for i in range(sequence_length, len(X)):
                sequences.append(X[i - sequence_length:i])
            
            if len(sequences) < 2:
                return np.zeros(len(X)), np.zeros(len(X))
            
            X_seq = np.array(sequences)
            
            # Normalize
            X_mean = np.mean(X_seq, axis=(0, 1))
            X_std = np.std(X_seq, axis=(0, 1)) + 1e-8
            X_norm = (X_seq - X_mean) / X_std
            
            X_tensor = torch.FloatTensor(X_norm)
            
            # Initialize model
            input_dim = X.shape[1]
            model = LSTMAutoencoder(input_dim, hidden_dim=16, num_layers=1)
            
            # Quick training
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
            criterion = nn.MSELoss()
            
            model.train()
            for epoch in range(10):
                optimizer.zero_grad()
                reconstructed = model(X_tensor)
                loss = criterion(reconstructed, X_tensor)
                loss.backward()
                optimizer.step()
            
            # Calculate errors
            model.eval()
            with torch.no_grad():
                reconstructed = model(X_tensor)
                errors = torch.mean((X_tensor - reconstructed) ** 2, dim=(1, 2)).numpy()
            
            # Map back to original indices
            predictions = np.zeros(len(X))
            scores = np.zeros(len(X))
            
            # First sequence_length points have no prediction
            for i, error in enumerate(errors):
                idx = i + sequence_length
                if idx < len(X):
                    scores[idx] = error
            
            # Threshold
            threshold = np.percentile(scores[scores > 0], 90) if np.any(scores > 0) else np.max(scores)
            predictions = (scores > threshold).astype(int)
            
            return predictions, scores
        
        except Exception as e:
            logger.error(f"LSTM detection error: {e}")
            return np.zeros(len(X)), np.zeros(len(X))
    
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

