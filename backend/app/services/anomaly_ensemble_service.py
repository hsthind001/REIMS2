"""
Anomaly Ensemble Service

Combines multiple anomaly detectors with weighted ensemble scoring
and calculates detector agreement to reduce false positives.
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.anomaly_detection import AnomalyDetection

logger = logging.getLogger(__name__)


class AnomalyEnsembleService:
    """Service for ensemble anomaly scoring and detector agreement"""
    
    # Detector reliability weights (0-1 scale)
    DETECTOR_WEIGHTS = {
        'z_score': 0.85,
        'percentage_change': 0.80,
        'iforest': 0.90,  # Isolation Forest
        'lof': 0.85,      # Local Outlier Factor
        'ocsvm': 0.80,    # One-Class SVM
        'cusum': 0.75,    # CUSUM
        'prophet': 0.88,  # Prophet forecasting
        'arima': 0.85,    # ARIMA
        'ets': 0.82,      # Exponential Smoothing
        'autoencoder': 0.92,  # Deep learning
        'lstm': 0.90      # LSTM
    }
    
    # Minimum agreement threshold to suppress noise
    MIN_AGREEMENT_THRESHOLD = 0.3  # At least 30% of detectors must agree
    MIN_AGREEMENT_COUNT = 2  # At least 2 detectors must agree
    
    def __init__(self, db: Session):
        """
        Initialize anomaly ensemble service
        
        Args:
            db: Database session
        """
        self.db = db
    
    def calculate_ensemble_score(
        self,
        anomaly_id: int
    ) -> Dict[str, Any]:
        """
        Calculate ensemble score for an anomaly
        
        Args:
            anomaly_id: Anomaly detection ID
            
        Returns:
            Dict with ensemble_score (0-100) and detector_agreement (0-1)
        """
        anomaly = self.db.query(AnomalyDetection).filter(
            AnomalyDetection.id == anomaly_id
        ).first()
        
        if not anomaly:
            return {
                'error': f'Anomaly {anomaly_id} not found'
            }
        
        # Get detection methods used
        detection_methods = anomaly.detection_methods or []
        if not detection_methods:
            # Fallback to anomaly_type
            detection_methods = [anomaly.anomaly_type]
        
        # Calculate weighted ensemble score
        total_weight = 0.0
        weighted_sum = 0.0
        
        for method in detection_methods:
            weight = self.DETECTOR_WEIGHTS.get(method, 0.5)  # Default weight
            confidence = float(anomaly.confidence) if anomaly.confidence else 0.5
            
            # Use ensemble_confidence if available, otherwise use confidence
            if anomaly.ensemble_confidence:
                method_confidence = float(anomaly.ensemble_confidence)
            else:
                method_confidence = confidence
            
            weighted_sum += method_confidence * weight
            total_weight += weight
        
        # Calculate ensemble score (0-100)
        if total_weight > 0:
            ensemble_score = (weighted_sum / total_weight) * 100
        else:
            ensemble_score = float(anomaly.confidence) * 100 if anomaly.confidence else 50.0
        
        # Calculate detector agreement
        agreement = self.get_detector_agreement(anomaly_id)
        
        # Update anomaly with ensemble score
        anomaly.ensemble_confidence = Decimal(str(ensemble_score / 100))
        anomaly.anomaly_score = Decimal(str(ensemble_score))
        anomaly.is_consensus = agreement['agreement_percent'] >= self.MIN_AGREEMENT_THRESHOLD
        
        self.db.commit()
        
        return {
            'anomaly_id': anomaly_id,
            'ensemble_score': ensemble_score,
            'detector_agreement': agreement,
            'is_consensus': anomaly.is_consensus,
            'detection_methods': detection_methods
        }
    
    def get_detector_agreement(
        self,
        anomaly_id: int
    ) -> Dict[str, Any]:
        """
        Calculate detector agreement for an anomaly
        
        Args:
            anomaly_id: Anomaly detection ID
            
        Returns:
            Dict with agreement_percent, agreement_count, and detector_details
        """
        anomaly = self.db.query(AnomalyDetection).filter(
            AnomalyDetection.id == anomaly_id
        ).first()
        
        if not anomaly:
            return {
                'agreement_percent': 0.0,
                'agreement_count': 0,
                'total_detectors': 0,
                'detector_details': []
            }
        
        # Get detection methods
        detection_methods = anomaly.detection_methods or []
        if not detection_methods:
            detection_methods = [anomaly.anomaly_type]
        
        total_detectors = len(detection_methods)
        
        # Count how many detectors flagged this anomaly
        # For now, if detection_methods exists, all methods agree
        # In a more sophisticated implementation, we'd check if multiple
        # separate anomaly detections exist for the same field/period
        agreement_count = total_detectors
        
        # Check for similar anomalies (same field, same period) from different methods
        similar_anomalies = self.db.query(AnomalyDetection).filter(
            and_(
                AnomalyDetection.document_id == anomaly.document_id,
                AnomalyDetection.field_name == anomaly.field_name,
                AnomalyDetection.id != anomaly_id
            )
        ).all()
        
        # Count unique detection methods across similar anomalies
        all_methods = set(detection_methods)
        for similar in similar_anomalies:
            if similar.detection_methods:
                all_methods.update(similar.detection_methods)
            else:
                all_methods.add(similar.anomaly_type)
        
        agreement_count = len(all_methods)
        total_detectors = max(total_detectors, agreement_count)
        
        # Calculate agreement percentage
        if total_detectors > 0:
            agreement_percent = agreement_count / total_detectors
        else:
            agreement_percent = 0.0
        
        # Get detector details
        detector_details = []
        for method in all_methods:
            weight = self.DETECTOR_WEIGHTS.get(method, 0.5)
            detector_details.append({
                'method': method,
                'weight': weight,
                'flagged': method in detection_methods
            })
        
        return {
            'agreement_percent': agreement_percent,
            'agreement_count': agreement_count,
            'total_detectors': total_detectors,
            'detector_details': detector_details
        }
    
    def suppress_noise(
        self,
        anomaly_id: int
    ) -> bool:
        """
        Suppress noise when only 1 weak detector flags a small, immaterial change
        
        Args:
            anomaly_id: Anomaly detection ID
            
        Returns:
            True if anomaly should be suppressed, False otherwise
        """
        anomaly = self.db.query(AnomalyDetection).filter(
            AnomalyDetection.id == anomaly_id
        ).first()
        
        if not anomaly:
            return False
        
        # Get agreement
        agreement = self.get_detector_agreement(anomaly_id)
        
        # Suppress if:
        # 1. Only 1 detector flagged it
        # 2. Agreement is below threshold
        # 3. Impact amount is small (if available)
        should_suppress = False
        
        if agreement['agreement_count'] < self.MIN_AGREEMENT_COUNT:
            should_suppress = True
        
        if agreement['agreement_percent'] < self.MIN_AGREEMENT_THRESHOLD:
            should_suppress = True
        
        # Check impact amount if available
        if anomaly.impact_amount:
            # Suppress if impact is less than $100
            if abs(anomaly.impact_amount) < Decimal('100.00'):
                should_suppress = True
        
        # Check confidence
        if anomaly.confidence and float(anomaly.confidence) < 0.5:
            should_suppress = True
        
        if should_suppress:
            anomaly.context_suppressed = True
            anomaly.suppression_reason = (
                f"Suppressed: Only {agreement['agreement_count']} detector(s) flagged, "
                f"agreement {agreement['agreement_percent']*100:.1f}% below threshold"
            )
            self.db.commit()
            logger.info(f"Suppressed noise anomaly {anomaly_id}")
        
        return should_suppress
    
    def calculate_ensemble_for_document(
        self,
        document_id: int
    ) -> Dict[str, Any]:
        """
        Calculate ensemble scores for all anomalies in a document
        
        Args:
            document_id: Document upload ID
            
        Returns:
            Dict with summary statistics
        """
        anomalies = self.db.query(AnomalyDetection).filter(
            AnomalyDetection.document_id == document_id
        ).all()
        
        results = {
            'total_anomalies': len(anomalies),
            'processed': 0,
            'suppressed': 0,
            'consensus_count': 0,
            'average_ensemble_score': 0.0,
            'results': []
        }
        
        total_score = 0.0
        
        for anomaly in anomalies:
            # Calculate ensemble score
            ensemble_result = self.calculate_ensemble_score(anomaly.id)
            if 'error' not in ensemble_result:
                results['processed'] += 1
                total_score += ensemble_result['ensemble_score']
                
                if ensemble_result.get('is_consensus'):
                    results['consensus_count'] += 1
                
                # Check if should suppress
                if self.suppress_noise(anomaly.id):
                    results['suppressed'] += 1
                
                results['results'].append({
                    'anomaly_id': anomaly.id,
                    'field_name': anomaly.field_name,
                    'ensemble_score': ensemble_result['ensemble_score'],
                    'is_consensus': ensemble_result.get('is_consensus', False),
                    'suppressed': anomaly.context_suppressed or False
                })
        
        if results['processed'] > 0:
            results['average_ensemble_score'] = total_score / results['processed']
        
        return results

