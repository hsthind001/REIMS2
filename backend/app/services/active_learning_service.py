"""
Active Learning Service

Monitors false positive rate, retrains models, adjusts detector weights,
and tracks model performance over time.
"""

from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import numpy as np
import os
import logging

from app.models.anomaly_detection import AnomalyDetection
from app.models.anomaly_feedback import AnomalyFeedback
from app.services.anomaly_risk_scorer import AnomalyRiskScorer
from app.services.enhanced_anomaly_ensemble import EnhancedAnomalyEnsemble

logger = logging.getLogger(__name__)


class ActiveLearningService:
    """
    Active learning service for continuous model improvement.
    
    Features:
    - Monitor false positive rate
    - Trigger retraining when FPR exceeds threshold
    - Adjust detector weights from feedback
    - Track model performance metrics
    """
    
    def __init__(self, db: Session):
        """Initialize active learning service."""
        self.db = db
        self.active_learning_enabled = os.getenv('ACTIVE_LEARNING_ENABLED', 'true').lower() == 'true'
        self.fpr_threshold = 0.25  # 25% false positive rate triggers retraining
        self.precision_threshold = 0.70  # Precision below 70% triggers retraining
        self.risk_scorer = AnomalyRiskScorer(db)
        self.ensemble = EnhancedAnomalyEnsemble(db)
    
    def monitor_and_retrain(self) -> Dict[str, Any]:
        """
        Monitor model performance and trigger retraining if needed.
        
        Returns:
            Dict with monitoring results and retraining status
        """
        if not self.active_learning_enabled:
            return {'enabled': False, 'message': 'Active learning disabled'}
        
        # Calculate performance metrics
        metrics = self._calculate_performance_metrics()
        
        # Check if retraining needed
        retrain_needed = False
        retrain_reason = None
        
        if metrics['false_positive_rate'] > self.fpr_threshold:
            retrain_needed = True
            retrain_reason = f"False positive rate ({metrics['false_positive_rate']:.1%}) exceeds threshold ({self.fpr_threshold:.1%})"
        
        if metrics['precision'] < self.precision_threshold:
            retrain_needed = True
            retrain_reason = f"Precision ({metrics['precision']:.1%}) below threshold ({self.precision_threshold:.1%})"
        
        if retrain_needed:
            # Trigger retraining
            retraining_results = self._trigger_retraining(retrain_reason)
            
            return {
                'enabled': True,
                'retrain_triggered': True,
                'retrain_reason': retrain_reason,
                'metrics': metrics,
                'retraining_results': retraining_results
            }
        else:
            return {
                'enabled': True,
                'retrain_triggered': False,
                'metrics': metrics,
                'message': 'Performance within acceptable range'
            }
    
    def _calculate_performance_metrics(
        self,
        lookback_days: int = 30
    ) -> Dict[str, float]:
        """
        Calculate model performance metrics from feedback.
        
        Returns:
            Dict with precision, recall, F1-score, false positive rate
        """
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        
        feedback = self.db.query(AnomalyFeedback).filter(
            AnomalyFeedback.created_at >= cutoff_date
        ).all()
        
        if len(feedback) < 10:
            return {
                'precision': 0.0,
                'recall': 0.0,
                'f1_score': 0.0,
                'false_positive_rate': 0.0,
                'sample_size': len(feedback)
            }
        
        # Calculate metrics
        true_positives = sum(1 for fb in feedback if fb.is_anomaly and fb.feedback_type == 'confirmed')
        false_positives = sum(1 for fb in feedback if not fb.is_anomaly or fb.feedback_type == 'dismissed')
        false_negatives = sum(1 for fb in feedback if fb.is_anomaly and fb.feedback_type == 'dismissed')
        
        # Precision = TP / (TP + FP)
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        
        # Recall = TP / (TP + FN)
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        
        # F1 Score = 2 * (Precision * Recall) / (Precision + Recall)
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        # False Positive Rate = FP / (FP + TN)
        # For simplicity, assume all non-anomalies are true negatives
        false_positive_rate = false_positives / len(feedback) if len(feedback) > 0 else 0.0
        
        return {
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score,
            'false_positive_rate': false_positive_rate,
            'true_positives': true_positives,
            'false_positives': false_positives,
            'false_negatives': false_negatives,
            'sample_size': len(feedback)
        }
    
    def _trigger_retraining(self, reason: str) -> Dict[str, Any]:
        """
        Trigger model retraining and weight adjustment.
        
        Args:
            reason: Reason for retraining
            
        Returns:
            Dict with retraining results
        """
        logger.info(f"Triggering model retraining: {reason}")
        
        # 1. Recalibrate ensemble weights
        ensemble_weights = self.ensemble.calibrate_thresholds_from_feedback()
        
        # 2. Recalibrate risk scorer weights
        risk_scorer_weights = self.risk_scorer.calibrate_weights_from_feedback()
        
        # 3. Log retraining event
        retraining_log = {
            'timestamp': datetime.utcnow().isoformat(),
            'reason': reason,
            'ensemble_weights_updated': True,
            'risk_scorer_weights_updated': True,
            'new_weights': {
                'ensemble': ensemble_weights,
                'risk_scorer': risk_scorer_weights
            }
        }
        
        logger.info(f"Model retraining complete: {retraining_log}")
        
        return retraining_log
    
    def track_model_performance(self) -> Dict[str, Any]:
        """
        Track and log model performance metrics over time.
        
        Returns:
            Dict with performance tracking data
        """
        metrics = self._calculate_performance_metrics(lookback_days=90)
        
        # Store metrics (in production, would store in model_performance_metrics table)
        performance_log = {
            'timestamp': datetime.utcnow().isoformat(),
            'metrics': metrics,
            'status': 'healthy' if metrics['precision'] >= self.precision_threshold and metrics['false_positive_rate'] <= self.fpr_threshold else 'degraded'
        }
        
        logger.info(f"Model performance tracking: {performance_log}")
        
        return performance_log
    
    def adjust_detector_weights(self) -> Dict[str, float]:
        """
        Adjust detector weights based on feedback.
        
        Returns:
            Updated weights dictionary
        """
        return self.risk_scorer.calibrate_weights_from_feedback()
