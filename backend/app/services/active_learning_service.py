"""
Active Learning Service for Anomaly Detection

Implements active learning to improve anomaly detection accuracy over time:
- User feedback collection and analysis
- Pattern learning from feedback
- Auto-suppression of learned false positives
- Confidence calibration
- Model retraining triggers
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import logging

from app.models.anomaly_detection import AnomalyDetection
from app.models.anomaly_feedback import AnomalyFeedback, AnomalyLearningPattern
from app.core.config import settings
from app.core.feature_flags import FeatureFlags

logger = logging.getLogger(__name__)


class ActiveLearningService:
    """
    Active learning service for improving anomaly detection through user feedback.
    
    Features:
    - Collects and analyzes user feedback on anomalies
    - Learns patterns from feedback to suppress false positives
    - Calibrates confidence scores based on historical accuracy
    - Triggers model retraining when patterns change
    """
    
    def __init__(self, db: Session):
        """Initialize active learning service."""
        self.db = db
        self.enabled = FeatureFlags.is_active_learning_enabled()
        self.auto_suppression_enabled = FeatureFlags.is_auto_suppression_enabled()
        self.feedback_lookback_days = settings.FEEDBACK_LOOKBACK_DAYS
        self.auto_suppression_threshold = settings.AUTO_SUPPRESSION_CONFIDENCE_THRESHOLD
    
    def record_feedback(
        self,
        anomaly_id: int,
        user_id: int,
        feedback_type: str,  # 'true_positive', 'false_positive', 'needs_review'
        feedback_notes: Optional[str] = None,
        business_context: Optional[Dict[str, Any]] = None
    ) -> AnomalyFeedback:
        """
        Record user feedback on an anomaly detection.
        
        Args:
            anomaly_id: ID of the anomaly detection
            user_id: ID of the user providing feedback
            feedback_type: Type of feedback
            feedback_notes: Optional notes from user
            business_context: Optional business context information
        
        Returns:
            AnomalyFeedback object
        """
        if not self.enabled:
            logger.warning("Active learning is disabled")
            return None
        
        # Get anomaly
        anomaly = self.db.query(AnomalyDetection).filter(
            AnomalyDetection.id == anomaly_id
        ).first()
        
        if not anomaly:
            raise ValueError(f"Anomaly {anomaly_id} not found")
        
        # Create feedback record
        feedback = AnomalyFeedback(
            anomaly_detection_id=anomaly_id,
            user_id=user_id,
            feedback_type=feedback_type,
            notes=feedback_notes,
            business_context=business_context,
            feedback_confidence=1.0,  # User feedback is always high confidence
            is_anomaly=feedback_type == 'true_positive',  # Set based on feedback type
            account_code=anomaly.account_code,
            anomaly_type=anomaly.anomaly_type,
            severity=anomaly.severity
        )
        
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        
        # Analyze feedback for pattern learning
        if feedback_type == 'false_positive':
            self._learn_false_positive_pattern(anomaly, feedback)
        
        return feedback
    
    def _learn_false_positive_pattern(
        self,
        anomaly: AnomalyDetection,
        feedback: AnomalyFeedback
    ):
        """
        Learn patterns from false positive feedback to suppress similar anomalies.
        
        Args:
            anomaly: The anomaly that was marked as false positive
            feedback: The feedback record
        """
        if not self.auto_suppression_enabled:
            return
        
        # Check if similar pattern already exists
        existing_pattern = self.db.query(AnomalyLearningPattern).filter(
            and_(
                AnomalyLearningPattern.property_id == anomaly.property_id,
                AnomalyLearningPattern.account_code == anomaly.account_code,
                AnomalyLearningPattern.anomaly_type == anomaly.anomaly_type,
                AnomalyLearningPattern.pattern_active == True
            )
        ).first()
        
        if existing_pattern:
            # Update existing pattern
            existing_pattern.occurrence_count += 1
            existing_pattern.last_applied_at = datetime.utcnow()
            existing_pattern.confidence = min(
                1.0,
                float(existing_pattern.confidence or 0.5) + 0.1
            )
        else:
            # Create new pattern
            pattern = AnomalyLearningPattern(
                property_id=anomaly.property_id,
                account_code=anomaly.account_code,
                anomaly_type=anomaly.anomaly_type,
                pattern_type='always_dismiss',  # False positives should be dismissed
                condition=f'{{"anomaly_type": "{anomaly.anomaly_type}", "account_code": "{anomaly.account_code}"}}',
                occurrence_count=1,
                confidence=0.5,  # Start with moderate confidence
                auto_suppress=True  # Enable auto-suppression
            )
            self.db.add(pattern)
        
        self.db.commit()
    
    def should_suppress_anomaly(
        self,
        anomaly: AnomalyDetection
    ) -> tuple[bool, Optional[AnomalyLearningPattern]]:
        """
        Check if an anomaly should be suppressed based on learned patterns.
        
        Args:
            anomaly: The anomaly to check
        
        Returns:
            Tuple of (should_suppress, pattern) where pattern is the matching pattern if found
        """
        if not self.auto_suppression_enabled:
            return False, None
        
        # Find matching patterns
        patterns = self.db.query(AnomalyLearningPattern).filter(
            and_(
                AnomalyLearningPattern.property_id == anomaly.property_id,
                AnomalyLearningPattern.account_code == anomaly.account_code,
                AnomalyLearningPattern.anomaly_type == anomaly.anomaly_type,
                AnomalyLearningPattern.auto_suppress == True,
                AnomalyLearningPattern.confidence >= self.auto_suppression_threshold
            )
        ).all()
        
        if patterns:
            # Use the pattern with highest confidence
            best_pattern = max(patterns, key=lambda p: float(p.confidence or 0))
            return True, best_pattern
        
        return False, None
    
    def get_feedback_statistics(
        self,
        property_id: Optional[int] = None,
        days: int = 90
    ) -> Dict[str, Any]:
        """
        Get feedback statistics for analysis.
        
        Args:
            property_id: Optional property ID to filter by
            days: Number of days to look back
        
        Returns:
            Dictionary with feedback statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = self.db.query(AnomalyFeedback).join(
            AnomalyDetection
        ).filter(
            AnomalyFeedback.created_at >= cutoff_date
        )
        
        if property_id:
            query = query.filter(AnomalyDetection.property_id == property_id)
        
        feedbacks = query.all()
        
        stats = {
            'total_feedback': len(feedbacks),
            'true_positives': sum(1 for f in feedbacks if f.feedback_type == 'true_positive'),
            'false_positives': sum(1 for f in feedbacks if f.feedback_type == 'false_positive'),
            'needs_review': sum(1 for f in feedbacks if f.feedback_type == 'needs_review'),
            'accuracy_rate': 0.0,
            'false_positive_rate': 0.0
        }
        
        if stats['total_feedback'] > 0:
            reviewed = stats['true_positives'] + stats['false_positives']
            if reviewed > 0:
                stats['accuracy_rate'] = stats['true_positives'] / reviewed
                stats['false_positive_rate'] = stats['false_positives'] / reviewed
        
        return stats
    
    def get_learned_patterns(
        self,
        property_id: Optional[int] = None,
        active_only: bool = True
    ) -> List[AnomalyLearningPattern]:
        """
        Get learned patterns for analysis or review.
        
        Args:
            property_id: Optional property ID to filter by
            active_only: Only return active patterns
        
        Returns:
            List of AnomalyLearningPattern objects
        """
        query = self.db.query(AnomalyLearningPattern)
        
        if property_id:
            query = query.filter(AnomalyLearningPattern.property_id == property_id)
        
        if active_only:
            query = query.filter(AnomalyLearningPattern.pattern_active == True)
        
        return query.order_by(
            AnomalyLearningPattern.confidence.desc()
        ).all()
    
    def deactivate_pattern(
        self,
        pattern_id: int,
        reason: Optional[str] = None
    ) -> bool:
        """
        Deactivate a learned pattern (e.g., if it's no longer valid).
        
        Args:
            pattern_id: ID of the pattern to deactivate
            reason: Optional reason for deactivation
        
        Returns:
            True if successful
        """
        pattern = self.db.query(AnomalyLearningPattern).filter(
            AnomalyLearningPattern.id == pattern_id
        ).first()
        
        if not pattern:
            return False
        
        pattern.auto_suppress = False
        pattern.updated_at = datetime.utcnow()
        
        self.db.commit()
        return True
