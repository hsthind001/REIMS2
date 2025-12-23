"""
Anomaly Risk Scorer Service

Implements unified risk scoring engine that combines all detector outputs
into a single 0-100 risk score.

Weights detectors by:
- Account type (revenue vs expense)
- Property maturity (new vs established)
- Historical accuracy per detector

Calibrates using feedback data.
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import numpy as np
import logging

from app.models.anomaly_detection import AnomalyDetection
from app.models.anomaly_feedback import AnomalyFeedback
from app.models.chart_of_accounts import ChartOfAccounts
from app.models.property import Property

logger = logging.getLogger(__name__)


class AnomalyRiskScorer:
    """
    Combines outputs from various anomaly detectors into a unified risk score (0-100).
    
    The risk score is calculated using weighted ensemble of:
    - Statistical methods (Z-score, percentage change)
    - ML methods (Isolation Forest, LOF, Autoencoder)
    - Seasonal/Forecast methods
    - Cross-statement checks
    
    Weights are calibrated based on:
    - Account type (revenue vs expense)
    - Property maturity
    - Historical accuracy per detector
    """
    
    def __init__(self, db: Session):
        """Initialize anomaly risk scorer."""
        self.db = db
        
        # Default detector weights (will be calibrated from feedback)
        self.default_weights = {
            'statistical_zscore': 0.20,
            'statistical_pct_change': 0.15,
            'ml_iforest': 0.15,
            'ml_lof': 0.10,
            'ml_ocsvm': 0.10,
            'seasonal': 0.15,
            'forecast_residual': 0.10,
            'robust_mad': 0.05,
        }
        
        # Account type multipliers
        self.account_type_multipliers = {
            'revenue': 1.2,  # Revenue anomalies are more critical
            'expense': 1.0,
            'asset': 0.9,
            'liability': 1.1,
            'equity': 0.8,
        }
        
        # Property maturity multipliers
        self.maturity_multipliers = {
            'new': 1.3,  # New properties have less historical data
            'established': 1.0,
        }
    
    def calculate_unified_risk_score(
        self,
        anomaly_detections: List[AnomalyDetection],
        property_id: int,
        account_code: str
    ) -> Dict[str, Any]:
        """
        Calculate unified risk score (0-100) from multiple anomaly detections.
        
        Args:
            anomaly_detections: List of AnomalyDetection records
            property_id: Property ID
            account_code: Account code being analyzed
            
        Returns:
            Dict with unified risk score and component breakdown
        """
        if not anomaly_detections:
            return {
                'risk_score': 0.0,
                'components': {},
                'confidence': 0.0
            }
        
        # Get account type and property maturity
        account_type = self._get_account_type(account_code)
        property_maturity = self._get_property_maturity(property_id)
        
        # Get calibrated weights for this account/property combination
        weights = self._get_calibrated_weights(account_type, property_maturity)
        
        # Calculate component scores
        component_scores = {}
        weighted_sum = 0.0
        total_weight = 0.0
        
        for detection in anomaly_detections:
            # Determine detector type
            detector_type = self._identify_detector_type(detection)
            
            # Calculate component score (0-100)
            component_score = self._calculate_component_score(detection)
            
            # Get weight for this detector
            weight = weights.get(detector_type, 0.1)
            
            # Apply account type and maturity multipliers
            adjusted_weight = weight * self.account_type_multipliers.get(account_type, 1.0) * self.maturity_multipliers.get(property_maturity, 1.0)
            
            component_scores[detector_type] = {
                'score': component_score,
                'weight': adjusted_weight,
                'raw_score': component_score,
                'detection_id': detection.id
            }
            
            weighted_sum += component_score * adjusted_weight
            total_weight += adjusted_weight
        
        # Normalize to 0-100
        if total_weight > 0:
            unified_score = min(100.0, max(0.0, weighted_sum / total_weight))
        else:
            unified_score = 0.0
        
        # Calculate confidence based on number of detectors and agreement
        confidence = self._calculate_confidence(anomaly_detections, component_scores)
        
        return {
            'risk_score': unified_score,
            'components': component_scores,
            'confidence': confidence,
            'account_type': account_type,
            'property_maturity': property_maturity,
            'detector_count': len(anomaly_detections)
        }
    
    def _identify_detector_type(self, detection: AnomalyDetection) -> str:
        """Identify the detector type from anomaly detection record."""
        # Check baseline_type first
        if detection.baseline_type:
            if detection.baseline_type.value == 'seasonal':
                return 'seasonal'
            elif detection.baseline_type.value == 'forecast':
                return 'forecast_residual'
        
        # Check anomaly_type
        if detection.anomaly_type == 'statistical':
            if detection.z_score:
                return 'statistical_zscore'
            elif detection.percentage_change:
                return 'statistical_pct_change'
        elif detection.anomaly_type == 'ml':
            # Check forecast_method or metadata for ML method
            if detection.forecast_method:
                return f'ml_{detection.forecast_method.lower()}'
            # Default ML
            return 'ml_iforest'
        elif detection.anomaly_type == 'robust_statistical':
            return 'robust_mad'
        elif detection.anomaly_type == 'cross_statement':
            return 'cross_statement'
        
        # Default
        return 'statistical_zscore'
    
    def _calculate_component_score(self, detection: AnomalyDetection) -> float:
        """
        Calculate component score (0-100) from a single detection.
        
        Combines:
        - Z-score magnitude
        - Percentage change
        - Severity
        - Confidence
        """
        score = 0.0
        
        # Base score from Z-score (0-50 points)
        if detection.z_score:
            z_abs = abs(float(detection.z_score))
            z_score_component = min(50.0, z_abs * 10.0)  # 5.0 Z-score = 50 points
            score += z_score_component
        
        # Percentage change component (0-30 points)
        if detection.percentage_change:
            pct_abs = abs(float(detection.percentage_change))
            pct_score_component = min(30.0, pct_abs / 2.0)  # 60% change = 30 points
            score += pct_score_component
        
        # Severity component (0-20 points)
        severity_scores = {
            'critical': 20.0,
            'high': 15.0,
            'medium': 10.0,
            'low': 5.0
        }
        score += severity_scores.get(detection.severity.lower(), 5.0)
        
        # Confidence multiplier (0-1)
        if detection.confidence:
            confidence_mult = float(detection.confidence)
            score *= confidence_mult
        
        return min(100.0, score)
    
    def _get_account_type(self, account_code: str) -> str:
        """Determine account type from account code."""
        # Chart of accounts typically uses first digit:
        # 1xxx = Assets
        # 2xxx = Liabilities
        # 3xxx = Equity
        # 4xxx = Revenue
        # 5xxx = Expenses
        
        if account_code and len(account_code) > 0:
            first_char = account_code[0]
            if first_char == '4':
                return 'revenue'
            elif first_char == '5':
                return 'expense'
            elif first_char == '1':
                return 'asset'
            elif first_char == '2':
                return 'liability'
            elif first_char == '3':
                return 'equity'
        
        return 'expense'  # Default
    
    def _get_property_maturity(self, property_id: int) -> str:
        """Determine property maturity (new vs established)."""
        property = self.db.query(Property).filter(Property.id == property_id).first()
        
        if property and property.acquisition_date:
            # Calculate years since acquisition
            years_owned = (datetime.utcnow() - property.acquisition_date).days / 365.0
            if years_owned < 2:
                return 'new'
        
        return 'established'
    
    def _get_calibrated_weights(
        self,
        account_type: str,
        property_maturity: str
    ) -> Dict[str, float]:
        """
        Get calibrated weights based on account type and property maturity.
        
        In production, this would query historical feedback to calibrate weights.
        For now, returns default weights with adjustments.
        """
        weights = self.default_weights.copy()
        
        # Adjust weights based on account type
        if account_type == 'revenue':
            # Revenue accounts: favor statistical and seasonal methods
            weights['statistical_zscore'] *= 1.2
            weights['seasonal'] *= 1.3
        elif account_type == 'expense':
            # Expense accounts: favor ML methods (more volatile)
            weights['ml_iforest'] *= 1.2
            weights['ml_lof'] *= 1.1
        
        # Adjust for property maturity
        if property_maturity == 'new':
            # New properties: favor simpler methods (less historical data)
            weights['statistical_zscore'] *= 1.2
            weights['statistical_pct_change'] *= 1.1
            weights['seasonal'] *= 0.8  # Less reliable with limited history
            weights['forecast_residual'] *= 0.7
        
        # Normalize weights to sum to 1.0
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        
        return weights
    
    def _calculate_confidence(
        self,
        detections: List[AnomalyDetection],
        component_scores: Dict[str, Any]
    ) -> float:
        """
        Calculate confidence in the unified risk score.
        
        Factors:
        - Number of detectors that agree
        - Consensus among detectors
        - Individual detector confidences
        """
        if not detections:
            return 0.0
        
        # Base confidence from number of detectors
        detector_count = len(detections)
        count_confidence = min(0.7, 0.3 + (detector_count * 0.1))
        
        # Consensus confidence (how many agree on high risk)
        high_risk_count = sum(1 for score in component_scores.values() if score['score'] > 50)
        consensus_ratio = high_risk_count / detector_count if detector_count > 0 else 0.0
        consensus_confidence = consensus_ratio * 0.3
        
        # Average individual confidence
        avg_confidence = np.mean([float(d.confidence) for d in detections if d.confidence])
        
        total_confidence = count_confidence + consensus_confidence + (avg_confidence * 0.2)
        return min(1.0, total_confidence)
    
    def update_anomaly_score(
        self,
        anomaly_id: int,
        risk_score: float
    ) -> bool:
        """
        Update anomaly_detections table with calculated risk score.
        
        Args:
            anomaly_id: AnomalyDetection ID
            risk_score: Calculated risk score (0-100)
            
        Returns:
            True if updated successfully
        """
        try:
            anomaly = self.db.query(AnomalyDetection).filter(
                AnomalyDetection.id == anomaly_id
            ).first()
            
            if anomaly:
                anomaly.anomaly_score = Decimal(str(risk_score))
                self.db.commit()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating anomaly score: {e}")
            self.db.rollback()
            return False
    
    def calibrate_weights_from_feedback(
        self,
        lookback_days: int = 90
    ) -> Dict[str, float]:
        """
        Calibrate detector weights based on historical feedback.
        
        Analyzes anomaly_feedback to determine which detectors are most accurate.
        Adjusts weights accordingly.
        
        Args:
            lookback_days: Number of days of feedback to analyze
            
        Returns:
            Updated weights dictionary
        """
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        
        # Get feedback data
        feedback = self.db.query(AnomalyFeedback).join(
            AnomalyDetection
        ).filter(
            AnomalyFeedback.created_at >= cutoff_date
        ).all()
        
        if not feedback:
            logger.info("No feedback data available for calibration")
            return self.default_weights
        
        # Calculate accuracy per detector type
        detector_accuracy = {}
        detector_counts = {}
        
        for fb in feedback:
            detection = fb.anomaly_detection
            detector_type = self._identify_detector_type(detection)
            
            if detector_type not in detector_accuracy:
                detector_accuracy[detector_type] = {'correct': 0, 'total': 0}
                detector_counts[detector_type] = 0
            
            detector_counts[detector_type] += 1
            
            # Check if feedback indicates correct detection
            if fb.feedback_type == 'confirmed' or (fb.is_anomaly and fb.feedback_type != 'dismissed'):
                detector_accuracy[detector_type]['correct'] += 1
            detector_accuracy[detector_type]['total'] += 1
        
        # Calculate precision (correct / total)
        precision_scores = {}
        for detector_type, acc in detector_accuracy.items():
            if acc['total'] > 0:
                precision = acc['correct'] / acc['total']
                precision_scores[detector_type] = precision
            else:
                precision_scores[detector_type] = 0.5  # Default
        
        # Adjust weights based on precision
        calibrated_weights = self.default_weights.copy()
        for detector_type, precision in precision_scores.items():
            if detector_type in calibrated_weights:
                # Boost weight for high-precision detectors
                calibrated_weights[detector_type] *= (0.5 + precision)
        
        # Normalize
        total = sum(calibrated_weights.values())
        if total > 0:
            calibrated_weights = {k: v / total for k, v in calibrated_weights.items()}
        
        logger.info(f"Calibrated weights from {len(feedback)} feedback records")
        return calibrated_weights
