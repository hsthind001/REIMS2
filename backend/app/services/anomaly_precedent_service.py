"""
Anomaly Precedent Service

Queries similar anomalies and provides historical context for reviewers.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, extract
import logging

from app.models.anomaly_detection import AnomalyDetection
from app.models.anomaly_feedback import AnomalyFeedback

logger = logging.getLogger(__name__)


class AnomalyPrecedentService:
    """
    Finds similar anomalies and provides historical context.
    
    Queries by:
    - Same account code
    - Same property
    - Same month-of-year
    - Similar magnitude
    """
    
    def __init__(self, db: Session):
        """Initialize precedent service."""
        self.db = db
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = timedelta(hours=1)
    
    def find_similar_anomalies(
        self,
        anomaly_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find similar anomalies with historical context.
        
        Args:
            anomaly_id: Current anomaly ID
            limit: Maximum number of similar anomalies to return
            
        Returns:
            List of similar anomalies with feedback and resolution notes
        """
        anomaly = self.db.query(AnomalyDetection).filter(
            AnomalyDetection.id == anomaly_id
        ).first()
        
        if not anomaly:
            return []
        
        # Check cache
        cache_key = f"similar_{anomaly_id}"
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if datetime.utcnow() - cached_time < self.cache_ttl:
                return cached_data
        
        # Find similar anomalies
        similar = []
        
        # 1. Same account, same property
        same_account = self.db.query(AnomalyDetection).filter(
            and_(
                AnomalyDetection.id != anomaly_id,
                AnomalyDetection.field_name == anomaly.field_name,
                AnomalyDetection.property_id == anomaly.property_id if hasattr(anomaly, 'property_id') else True
            )
        ).order_by(AnomalyDetection.detected_at.desc()).limit(limit).all()
        
        # 2. Same account, different property (for cross-property patterns)
        same_account_diff_property = self.db.query(AnomalyDetection).filter(
            and_(
                AnomalyDetection.id != anomaly_id,
                AnomalyDetection.field_name == anomaly.field_name,
                AnomalyDetection.property_id != anomaly.property_id if hasattr(anomaly, 'property_id') else True
            )
        ).order_by(AnomalyDetection.detected_at.desc()).limit(5).all()
        
        # 3. Same month-of-year (seasonal patterns)
        if anomaly.detected_at:
            month = anomaly.detected_at.month
            same_month = self.db.query(AnomalyDetection).filter(
                and_(
                    AnomalyDetection.id != anomaly_id,
                    extract('month', AnomalyDetection.detected_at) == month,
                    AnomalyDetection.field_name == anomaly.field_name
                )
            ).order_by(AnomalyDetection.detected_at.desc()).limit(5).all()
        else:
            same_month = []
        
        # Combine and deduplicate
        all_similar = list(set(same_account + same_account_diff_property + same_month))
        
        # Enrich with feedback
        for similar_anomaly in all_similar[:limit]:
            feedback = self.db.query(AnomalyFeedback).filter(
                AnomalyFeedback.anomaly_detection_id == similar_anomaly.id
            ).order_by(AnomalyFeedback.created_at.desc()).first()
            
            similar.append({
                'anomaly_id': similar_anomaly.id,
                'detected_at': similar_anomaly.detected_at.isoformat() if similar_anomaly.detected_at else None,
                'field_name': similar_anomaly.field_name,
                'actual_value': float(similar_anomaly.field_value) if similar_anomaly.field_value else None,
                'expected_value': float(similar_anomaly.expected_value) if similar_anomaly.expected_value else None,
                'z_score': float(similar_anomaly.z_score) if similar_anomaly.z_score else None,
                'severity': similar_anomaly.severity,
                'similarity_reason': self._determine_similarity_reason(anomaly, similar_anomaly),
                'feedback': {
                    'is_anomaly': feedback.is_anomaly if feedback else None,
                    'feedback_type': feedback.feedback_type if feedback else None,
                    'resolution_notes': feedback.resolution_notes if feedback else None,
                    'created_at': feedback.created_at.isoformat() if feedback and feedback.created_at else None
                } if feedback else None
            })
        
        # Cache results
        self.cache[cache_key] = (similar, datetime.utcnow())
        
        return similar
    
    def _determine_similarity_reason(
        self,
        current: AnomalyDetection,
        similar: AnomalyDetection
    ) -> str:
        """Determine why this anomaly is similar."""
        reasons = []
        
        if current.field_name == similar.field_name:
            reasons.append("same_account")
        
        if hasattr(current, 'property_id') and hasattr(similar, 'property_id'):
            if current.property_id == similar.property_id:
                reasons.append("same_property")
            else:
                reasons.append("cross_property")
        
        if current.detected_at and similar.detected_at:
            if current.detected_at.month == similar.detected_at.month:
                reasons.append("same_month")
        
        return ", ".join(reasons) if reasons else "general"
