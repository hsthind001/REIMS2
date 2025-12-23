"""
Alert Suppression Service

Automatically suppresses alerts marked as false positives based on patterns.
Uses AUTO_SUPPRESSION_ENABLED and AUTO_SUPPRESSION_CONFIDENCE_THRESHOLD.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import os
import logging

from app.models.anomaly_detection import AnomalyDetection
from app.models.anomaly_feedback import AnomalyFeedback

logger = logging.getLogger(__name__)


class AlertSuppressionService:
    """
    Suppresses alerts based on false positive patterns.
    
    Analyzes anomaly_feedback to identify patterns and suppress similar alerts.
    """
    
    def __init__(self, db: Session):
        """Initialize suppression service."""
        self.db = db
        self.auto_suppression_enabled = os.getenv('AUTO_SUPPRESSION_ENABLED', 'true').lower() == 'true'
        self.confidence_threshold = float(os.getenv('AUTO_SUPPRESSION_CONFIDENCE_THRESHOLD', '0.8'))
    
    def check_and_suppress(
        self,
        anomaly_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Check if anomaly should be suppressed based on patterns.
        
        Args:
            anomaly_id: AnomalyDetection ID
            
        Returns:
            Suppression details if suppressed, None otherwise
        """
        if not self.auto_suppression_enabled:
            return None
        
        anomaly = self.db.query(AnomalyDetection).filter(
            AnomalyDetection.id == anomaly_id
        ).first()
        
        if not anomaly:
            return None
        
        # Check if already suppressed
        if anomaly.suppressed_until and anomaly.suppressed_until > datetime.utcnow():
            return {
                'suppressed': True,
                'reason': anomaly.suppression_reason,
                'until': anomaly.suppressed_until.isoformat()
            }
        
        # Analyze feedback patterns
        suppression_pattern = self._analyze_suppression_pattern(anomaly)
        
        if suppression_pattern and suppression_pattern.get('confidence', 0) >= self.confidence_threshold:
            # Suppress the anomaly
            suppression_duration = timedelta(days=suppression_pattern.get('suppress_days', 30))
            
            anomaly.suppressed_until = datetime.utcnow() + suppression_duration
            anomaly.suppression_reason = suppression_pattern.get('reason', 'Pattern-based suppression')
            
            self.db.commit()
            
            logger.info(f"Suppressed anomaly {anomaly_id} based on pattern: {suppression_pattern.get('reason')}")
            
            return {
                'suppressed': True,
                'reason': suppression_pattern.get('reason'),
                'confidence': suppression_pattern.get('confidence'),
                'until': anomaly.suppressed_until.isoformat()
            }
        
        return None
    
    def _analyze_suppression_pattern(
        self,
        anomaly: AnomalyDetection
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze feedback patterns to determine if anomaly should be suppressed.
        
        Returns:
            Dict with suppression pattern details or None
        """
        # Get feedback for similar anomalies
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        similar_feedback = self.db.query(AnomalyFeedback).join(
            AnomalyDetection
        ).filter(
            and_(
                AnomalyDetection.field_name == anomaly.field_name,
                AnomalyFeedback.created_at >= cutoff_date,
                or_(
                    AnomalyFeedback.feedback_type == 'dismissed',
                    and_(
                        AnomalyFeedback.is_anomaly == False,
                        AnomalyFeedback.feedback_type != 'confirmed'
                    )
                )
            )
        ).all()
        
        if len(similar_feedback) < 3:
            # Not enough feedback to establish pattern
            return None
        
        # Calculate false positive rate
        false_positive_count = sum(
            1 for fb in similar_feedback
            if fb.feedback_type == 'dismissed' or (not fb.is_anomaly and fb.feedback_type != 'confirmed')
        )
        
        false_positive_rate = false_positive_count / len(similar_feedback)
        
        if false_positive_rate >= 0.7:  # 70%+ false positive rate
            # High confidence suppression
            return {
                'confidence': min(0.95, 0.7 + (false_positive_rate - 0.7) * 0.5),
                'reason': f"High false positive rate ({false_positive_rate:.1%}) for similar anomalies",
                'suppress_days': 90 if false_positive_rate >= 0.9 else 30
            }
        
        # Check for specific account patterns
        if anomaly.field_name:
            account_feedback = [fb for fb in similar_feedback if fb.anomaly_detection.field_name == anomaly.field_name]
            
            if len(account_feedback) >= 5:
                account_fpr = sum(
                    1 for fb in account_feedback
                    if fb.feedback_type == 'dismissed' or (not fb.is_anomaly and fb.feedback_type != 'confirmed')
                ) / len(account_feedback)
                
                if account_fpr >= 0.8:
                    return {
                        'confidence': 0.85,
                        'reason': f"Account {anomaly.field_name} has high false positive rate ({account_fpr:.1%})",
                        'suppress_days': 60
                    }
        
        return None
    
    def review_suppressions(
        self,
        lookback_days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Review and update suppression rules based on recent feedback.
        
        Args:
            lookback_days: Days of feedback to analyze
            
        Returns:
            List of suppression updates
        """
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        
        # Get suppressed anomalies
        suppressed = self.db.query(AnomalyDetection).filter(
            and_(
                AnomalyDetection.suppressed_until.isnot(None),
                AnomalyDetection.suppressed_until > datetime.utcnow()
            )
        ).all()
        
        updates = []
        
        for anomaly in suppressed:
            # Check if suppression should be extended or removed
            pattern = self._analyze_suppression_pattern(anomaly)
            
            if pattern and pattern.get('confidence', 0) >= self.confidence_threshold:
                # Extend suppression if pattern still valid
                if anomaly.suppressed_until < datetime.utcnow() + timedelta(days=pattern.get('suppress_days', 30)):
                    anomaly.suppressed_until = datetime.utcnow() + timedelta(days=pattern.get('suppress_days', 30))
                    updates.append({
                        'anomaly_id': anomaly.id,
                        'action': 'extended',
                        'new_until': anomaly.suppressed_until.isoformat()
                    })
            else:
                # Remove suppression if pattern no longer valid
                anomaly.suppressed_until = None
                anomaly.suppression_reason = None
                updates.append({
                    'anomaly_id': anomaly.id,
                    'action': 'removed'
                })
        
        if updates:
            self.db.commit()
        
        return updates
