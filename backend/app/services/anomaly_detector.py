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
        historical_values: List[float],
        threshold_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Detect anomalies using multiple statistical methods.
        
        Args:
            document_id: Document ID
            field_name: Field/account code name
            current_value: Current period value
            historical_values: List of historical values for comparison
            threshold_value: Absolute value threshold (if None, uses default percentage-based logic)
        
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
        
        # Absolute value or percentage change detection (works with 1+ values)
        if threshold_value is not None:
            # Use absolute value threshold
            abs_anomaly = self._detect_absolute_value_anomaly(current_value, historical_values, threshold_value)
            if abs_anomaly:
                anomalies.append(abs_anomaly)
        else:
            # Fallback to percentage-based detection (for backward compatibility)
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
    
    def _detect_absolute_value_anomaly(
        self,
        value: float,
        historical_values: List[float],
        threshold_value: float
    ) -> Optional[Dict]:
        """
        Detect anomaly using absolute value threshold.
        
        Anomaly is detected if: abs(current_value - expected_value) > threshold_value
        """
        if not historical_values:
            return None
        
        # Use average of all historical values (or single value if only one)
        recent_avg = statistics.mean(historical_values) if len(historical_values) > 0 else None
        
        if recent_avg is None:
            return None
        
        # Calculate absolute difference
        absolute_difference = abs(value - recent_avg)
        
        # Check if difference exceeds threshold
        if absolute_difference > threshold_value:
            # Calculate percentage change for display purposes
            if recent_avg != 0:
                pct_change = ((value - recent_avg) / recent_avg) * 100
            else:
                pct_change = 0.0
            
            # Determine severity based on how much the threshold is exceeded
            threshold_exceeded_ratio = absolute_difference / threshold_value if threshold_value > 0 else 0
            
            severity = "critical" if threshold_exceeded_ratio > 3.0 else "high" if threshold_exceeded_ratio > 2.0 else "medium"
            
            return {
                "type": "absolute_value_change",
                "absolute_difference": round(absolute_difference, 2),
                "percentage_change": round(pct_change, 2),  # For display purposes
                "threshold_value": threshold_value,
                "severity": severity
            }
        
        return None
    
    def _detect_percentage_change(
        self,
        value: float,
        historical_values: List[float]
    ) -> Optional[Dict]:
        """Detect anomaly using percentage change (legacy method for backward compatibility)"""
        if not historical_values:
            return None
        
        # Use average of all historical values (or single value if only one)
        recent_avg = statistics.mean(historical_values) if len(historical_values) > 0 else None
        
        if recent_avg is None or recent_avg == 0:
            return None
        
        # Calculate percentage change preserving the sign (positive = increase, negative = decrease)
        pct_change = (value - recent_avg) / recent_avg
        pct_change_abs = abs(pct_change)
        
        # Check threshold using absolute value, but store the signed value
        if pct_change_abs > self.percentage_change_threshold:
            return {
                "type": "percentage_change",
                "percentage_change": round(pct_change * 100, 2),  # Preserve sign: positive for increase, negative for decrease
                "severity": "critical" if pct_change_abs > 0.5 else "high" if pct_change_abs > 0.25 else "medium"
            }
        
        return None

