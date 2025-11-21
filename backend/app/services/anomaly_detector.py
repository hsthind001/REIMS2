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
        self.z_score_threshold = 2.0  # Lowered from 3.0 to 2.0 for more sensitive detection (2 sigma)
        self.percentage_change_threshold = 0.15  # Lowered from 0.25 to 0.15 (15% change) for more sensitive detection
    
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
        
        if len(historical_values) < 1:
            return {"anomalies": [], "insufficient_data": True}
        
        # Z-score detection (requires 2+ values for standard deviation)
        if len(historical_values) >= 2:
            z_anomaly = self._detect_z_score_anomaly(current_value, historical_values)
            if z_anomaly:
                anomalies.append(z_anomaly)
        
        # Percentage change detection (works with 1+ values)
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
        
        # Use average of all historical values (or single value if only one)
        recent_avg = statistics.mean(historical_values) if len(historical_values) > 0 else None
        
        if recent_avg is None or recent_avg == 0:
            return None
        
        pct_change = abs((value - recent_avg) / recent_avg)
        
        if pct_change > self.percentage_change_threshold:
            return {
                "type": "percentage_change",
                "percentage_change": round(pct_change * 100, 2),
                "severity": "critical" if pct_change > 0.5 else "high" if pct_change > 0.25 else "medium"
            }
        
        return None

