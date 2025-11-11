"""
Active Learning Service for REIMS2
Implements feedback loop for continuous improvement from human corrections.

Sprint 2: AI/ML Intelligence Layer
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.extraction_field_metadata import ExtractionFieldMetadata
from app.models.validation_result import ValidationResult
from app.db.database import get_db


class ActiveLearningService:
    """
    Service to identify uncertain fields and improve extraction over time.
    
    Features:
    - Identifies low-confidence fields for human review
    - Tracks correction patterns
    - Updates confidence thresholds based on validation history
    - Queues fields for retraining (future: Sprint 5)
    """
    
    def __init__(self, db: Session):
        """
        Initialize active learning service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.confidence_threshold = 0.70  # Initial threshold
        self.review_priority_map = {
            (0.0, 0.5): 'critical',
            (0.5, 0.7): 'high',
            (0.7, 0.8): 'medium',
            (0.8, 1.0): 'low'
        }
    
    def identify_uncertain_fields(
        self,
        document_id: Optional[int] = None,
        table_name: Optional[str] = None,
        limit: int = 100
    ) -> List[ExtractionFieldMetadata]:
        """
        Identify fields with low confidence that need human review.
        
        Args:
            document_id: Optional filter by document
            table_name: Optional filter by table (balance_sheet, income_statement, etc.)
            limit: Maximum number of fields to return
            
        Returns:
            List of uncertain field metadata ordered by priority
        """
        query = self.db.query(ExtractionFieldMetadata).filter(
            ExtractionFieldMetadata.needs_review == True,
            ExtractionFieldMetadata.reviewed_at.is_(None)
        )
        
        if document_id:
            query = query.filter(ExtractionFieldMetadata.document_id == document_id)
        
        if table_name:
            query = query.filter(ExtractionFieldMetadata.table_name == table_name)
        
        # Order by review priority and confidence (lowest first)
        query = query.order_by(
            ExtractionFieldMetadata.review_priority.desc(),
            ExtractionFieldMetadata.confidence_score.asc()
        )
        
        return query.limit(limit).all()
    
    def queue_for_human_review(
        self,
        metadata_id: int,
        reason: str,
        priority: str = 'medium'
    ) -> bool:
        """
        Queue a field for human review with specific reason.
        
        Args:
            metadata_id: ID of extraction field metadata
            reason: Reason for review
            priority: Priority level (critical, high, medium, low)
            
        Returns:
            True if successfully queued
        """
        try:
            metadata = self.db.query(ExtractionFieldMetadata).filter(
                ExtractionFieldMetadata.id == metadata_id
            ).first()
            
            if not metadata:
                return False
            
            metadata.needs_review = True
            metadata.review_priority = priority
            metadata.flagged_reason = reason
            
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            print(f"Error queuing field for review: {e}")
            return False
    
    def record_human_correction(
        self,
        metadata_id: int,
        corrected_value: str,
        reviewer_id: int
    ) -> Dict[str, Any]:
        """
        Record a human correction and calculate accuracy metrics.
        
        Args:
            metadata_id: ID of extraction field metadata
            corrected_value: Human-corrected value
            reviewer_id: ID of user who made correction
            
        Returns:
            Dict with correction metrics
        """
        try:
            metadata = self.db.query(ExtractionFieldMetadata).filter(
                ExtractionFieldMetadata.id == metadata_id
            ).first()
            
            if not metadata:
                return {'error': 'Metadata not found'}
            
            # Get original extracted value (from record)
            original_value = self._get_field_value(
                metadata.table_name,
                metadata.record_id,
                metadata.field_name
            )
            
            # Calculate if correction was needed
            was_correct = self._values_match(original_value, corrected_value)
            
            # Update metadata
            metadata.reviewed_at = datetime.utcnow()
            metadata.reviewed_by = reviewer_id
            metadata.needs_review = False
            
            self.db.commit()
            
            # Learn from this correction
            self._update_engine_performance(
                engine_name=metadata.extraction_engine,
                field_name=metadata.field_name,
                was_correct=was_correct,
                confidence=float(metadata.confidence_score)
            )
            
            return {
                'metadata_id': metadata_id,
                'was_correct': was_correct,
                'original_value': original_value,
                'corrected_value': corrected_value,
                'confidence_score': float(metadata.confidence_score),
                'engine': metadata.extraction_engine
            }
        except Exception as e:
            self.db.rollback()
            return {'error': str(e)}
    
    def update_confidence_thresholds(
        self,
        lookback_days: int = 30
    ) -> Dict[str, float]:
        """
        Update confidence thresholds based on validation history.
        
        Analyzes the last N days of validations to determine optimal thresholds
        for each engine and field type.
        
        Args:
            lookback_days: Number of days to analyze
            
        Returns:
            Dict of updated thresholds by engine
        """
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        
        # Get validation statistics by engine
        stats = self.db.query(
            ExtractionFieldMetadata.extraction_engine,
            func.avg(ExtractionFieldMetadata.confidence_score).label('avg_confidence'),
            func.count(ExtractionFieldMetadata.id).label('total'),
            func.sum(
                func.cast(ExtractionFieldMetadata.needs_review == False, func.Integer())
            ).label('correct')
        ).filter(
            ExtractionFieldMetadata.created_at >= cutoff_date,
            ExtractionFieldMetadata.reviewed_at.isnot(None)
        ).group_by(
            ExtractionFieldMetadata.extraction_engine
        ).all()
        
        updated_thresholds = {}
        
        for engine, avg_conf, total, correct in stats:
            if total > 10:  # Minimum sample size
                accuracy_rate = (correct or 0) / total
                
                # If accuracy is high (>95%), we can lower the review threshold
                if accuracy_rate > 0.95:
                    new_threshold = max(0.6, avg_conf * 0.8)
                # If accuracy is low (<85%), raise the threshold
                elif accuracy_rate < 0.85:
                    new_threshold = min(0.9, avg_conf * 1.2)
                else:
                    new_threshold = 0.70  # Default
                
                updated_thresholds[engine] = round(new_threshold, 2)
        
        return updated_thresholds
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """
        Get statistics on active learning progress.
        
        Returns:
            Dict with learning metrics
        """
        # Fields reviewed in last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        reviewed_count = self.db.query(func.count(ExtractionFieldMetadata.id)).filter(
            ExtractionFieldMetadata.reviewed_at.isnot(None),
            ExtractionFieldMetadata.reviewed_at >= thirty_days_ago
        ).scalar()
        
        # Fields pending review
        pending_count = self.db.query(func.count(ExtractionFieldMetadata.id)).filter(
            ExtractionFieldMetadata.needs_review == True,
            ExtractionFieldMetadata.reviewed_at.is_(None)
        ).scalar()
        
        # Average confidence by engine
        engine_stats = self.db.query(
            ExtractionFieldMetadata.extraction_engine,
            func.avg(ExtractionFieldMetadata.confidence_score).label('avg_confidence'),
            func.count(ExtractionFieldMetadata.id).label('count')
        ).group_by(
            ExtractionFieldMetadata.extraction_engine
        ).all()
        
        return {
            'reviewed_last_30_days': reviewed_count or 0,
            'pending_review': pending_count or 0,
            'engine_statistics': [
                {
                    'engine': engine,
                    'avg_confidence': float(avg_conf) if avg_conf else 0.0,
                    'sample_count': count
                }
                for engine, avg_conf, count in engine_stats
            ],
            'current_threshold': self.confidence_threshold
        }
    
    def _get_field_value(self, table_name: str, record_id: int, field_name: str) -> Optional[str]:
        """Get the actual field value from the data table."""
        # This would query the actual data table (balance_sheet_data, etc.)
        # For now, return None as placeholder
        # TODO: Implement dynamic table query based on table_name
        return None
    
    def _values_match(self, value1: Any, value2: Any) -> bool:
        """Check if two values match (accounting for formatting differences)."""
        if value1 is None or value2 is None:
            return value1 == value2
        
        normalizer = NumericNormalizer()
        return normalizer.normalize(value1) == normalizer.normalize(value2)
    
    def _update_engine_performance(
        self,
        engine_name: str,
        field_name: str,
        was_correct: bool,
        confidence: float
    ):
        """
        Update engine performance metrics (to be implemented in Sprint 5).
        
        This will be used to adjust engine weights and confidence thresholds.
        """
        # Placeholder for future implementation
        # Will track: engine accuracy by field type, confidence calibration, etc.
        pass

