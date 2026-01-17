"""
Statistical Anomaly Service

Uses PyOD (Python Outlier Detection) to identify statistical anomalies in financial transactions.
Implements unsupervised learning models (ECOD, IForest) to catch "soft" fraud and errors.
"""

import logging
from typing import List, Dict, Any, Optional, Union
import numpy as np
import pandas as pd
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select

# Try to import PyOD, but handle case where it's not installed yet
try:
    from pyod.models.ecod import ECOD
    from pyod.models.iforest import IForest
    PYOD_AVAILABLE = True
except ImportError:
    PYOD_AVAILABLE = False


from app.models.income_statement_data import IncomeStatementData

logger = logging.getLogger(__name__)

class StatisticalAnomalyService:
    """
    Service for detection of statistical anomalies in financial data using PyOD.
    """

    def __init__(self, db: Session):
        self.db = db
        self.model = None
        self.model_type = "ECOD"  # Default to ECOD (Empirical Cumulative Distribution)
        
        if not PYOD_AVAILABLE:
            logger.warning("PyOD not available. Statistical anomaly detection will be disabled.")

    def train_model(self, data_points: List[IncomeStatementData]) -> bool:
        """
        Train the anomaly detection model on historical data.
        
        Args:
            data_points: List of historical income statement line items
            
        Returns:
            True if training successful, False otherwise
        """
        if not PYOD_AVAILABLE or not data_points:
            return False

        try:
            # Extract features for training
            X = self._extract_features(data_points)
            
            if X.empty:
                logger.warning("No valid features extracted for training")
                return False

            # Initialize model
            # Contamination is the expected percentage of outliers (e.g., 1%)
            contamination = 0.01
            
            if self.model_type == "ECOD":
                self.model = ECOD(contamination=contamination)
            else:
                self.model = IForest(contamination=contamination, random_state=42)
                
            # Fit model
            self.model.fit(X)
            
            logger.info(f"Successfully trained {self.model_type} model on {len(X)} data points")
            return True
            
        except Exception as e:
            logger.error(f"Error training statistical anomaly model: {e}")
            return False

    def detect_anomalies(self, data_points: List[IncomeStatementData]) -> List[Dict[str, Any]]:
        """
        Detect anomalies in a set of new data points.
        
        Args:
            data_points: List of line items to analyze
            
        Returns:
            List of dictionaries containing anomaly details for flagged items
        """
        if not PYOD_AVAILABLE or not self.model:
            logger.warning("Cannot detect anomalies: PyOD missing or model not trained")
            return []

        if not data_points:
            return []

        try:
            X = self._extract_features(data_points)
            
            if X.empty:
                return []

            # Predict anomalies (1 = outlier, 0 = inlier)
            predictions = self.model.predict(X)
            
            # Get anomaly scores (higher = more anomalous)
            scores = self.model.decision_function(X)
            
            # Get probability scores (0 to 1)
            probs = self.model.predict_proba(X)[:, 1]

            anomalies = []
            
            for i, (pred, score, prob) in enumerate(zip(predictions, scores, probs)):
                if pred == 1:  # It's an outlier
                    item = data_points[i]
                    
                    anomalies.append({
                        "item_id": item.id,
                        "description": item.account_name,
                        "amount": float(item.period_amount) if item.period_amount else 0.0,
                        "date": item.period_start_date,
                        "anomaly_score": float(score),
                        "anomaly_probability": float(prob),
                        "model_type": self.model_type,
                        "severity": "critical" if prob > 0.9 else "high" if prob > 0.7 else "medium",
                        "features": X.iloc[i].to_dict()
                    })

            return anomalies

        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return []

    def _extract_features(self, data_points: List[IncomeStatementData]) -> pd.DataFrame:
        """
        Extract numerical features for anomaly detection.
        
        Features:
        - Amount (absolute value)
        - Is round number (binary)
        """
        data = []
        
        for item in data_points:
            amount = float(item.period_amount) if item.period_amount else 0.0
            
            # Simple features for now as date parsing might be tricky with "Dec 2023" format
            features = {
                "amount_abs": abs(amount),
                "is_round_number": 1 if abs(amount) % 100 == 0 else 0,
            }
            data.append(features)
            
        return pd.DataFrame(data)

    def run_training_job_async(self, property_id: int):
        """
        Helper method to be called by a background task to retrain model.
        Fetches all historical data for a property.
        """
        try:
            stmt = select(IncomeStatementData).where(
                IncomeStatementData.property_id == property_id
            ).limit(5000) 
            
            result = self.db.execute(stmt)
            data_points = result.scalars().all()
            
            if len(data_points) > 50: 
                self.train_model(data_points)
                logger.info(f"Retrained anomaly model for property {property_id}")
            else:
                logger.info(f"Insufficient data to train model for property {property_id}")
                
        except Exception as e:
            logger.error(f"Failed training job for property {property_id}: {e}")
