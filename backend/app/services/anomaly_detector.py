"""
Statistical Anomaly Detector Service

Detects anomalies using Z-score, percentage change, missing data detection,
and historical baseline comparison.
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import statistics


class StatisticalAnomalyDetector:
    """
    Statistical anomaly detection using multiple methods.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.z_score_threshold = 3.0  # Standard: 3 sigma
        self.percentage_change_threshold = 0.25  # 25% change
    
    def detect_anomalies(
        self,
        document_id: int,
        field_name: str,
        current_value: float,
        historical_values: List[float]
    ) -> Dict[str, Any]:
        """
        Detect anomalies using multiple statistical methods.
        
        Returns:
            Dict with anomaly detection results
        """
        anomalies = []
        
        if len(historical_values) < 3:
            return {"anomalies": [], "insufficient_data": True}
        
        # Z-score detection
        z_anomaly = self._detect_z_score_anomaly(current_value, historical_values)
        if z_anomaly:
            anomalies.append(z_anomaly)
        
        # Percentage change detection
        pct_anomaly = self._detect_percentage_change(current_value, historical_values)
        if pct_anomaly:
            anomalies.append(pct_anomaly)
        
        return {
            "anomalies": anomalies,
            "field_name": field_name,
            "current_value": current_value
        }
    
    def _detect_z_score_anomaly(
        self,
        value: float,
        historical_values: List[float]
    ) -> Optional[Dict]:
        """Detect anomaly using Z-score"""
        if len(historical_values) < 2:
            return None
        
        mean = statistics.mean(historical_values)
        stdev = statistics.stdev(historical_values) if len(historical_values) > 1 else 0
        
        if stdev == 0:
            return None
        
        z_score = (value - mean) / stdev
        
        if abs(z_score) > self.z_score_threshold:
            return {
                "type": "z_score",
                "z_score": round(z_score, 4),
                "severity": "critical" if abs(z_score) > 4 else "high",
                "expected_range": (mean - 3 * stdev, mean + 3 * stdev)
            }
        
        return None
    
    def _detect_percentage_change(
        self,
        value: float,
        historical_values: List[float]
    ) -> Optional[Dict]:
        """Detect anomaly using percentage change"""
        if not historical_values:
            return None
        
        recent_avg = statistics.mean(historical_values[-3:]) if len(historical_values) >= 3 else historical_values[-1]
        
        if recent_avg == 0:
            return None
        
        pct_change = (value - recent_avg) / recent_avg
        
        if abs(pct_change) > self.percentage_change_threshold:
            return {
                "type": "percentage_change",
                "percentage_change": round(pct_change * 100, 2),
                "severity": "critical" if abs(pct_change) > 0.5 else "medium"
            }
        
        return None

