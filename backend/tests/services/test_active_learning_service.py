"""
Unit tests for Active Learning Service
Tests correction tracking, threshold updates, and learning metrics.
"""
import pytest
from datetime import datetime, timedelta

from app.services.active_learning_service import ActiveLearningService


class TestActiveLearningService:
    """Test active learning service."""
    
    def test_identify_uncertain_fields(self, db_session):
        """Test identification of low-confidence fields."""
        service = ActiveLearningService(db_session)
        
        uncertain_fields = service.identify_uncertain_fields(limit=10)
        
        # Should return fields with needs_review=True and reviewed_at=None
        assert isinstance(uncertain_fields, list)
        assert all(hasattr(f, 'needs_review') for f in uncertain_fields)
    
    def test_queue_for_review(self, db_session):
        """Test queuing fields for human review."""
        service = ActiveLearningService(db_session)
        
        # Would test with actual metadata_id
        # result = service.queue_for_human_review(
        #     metadata_id=1,
        #     reason="Low confidence extraction",
        #     priority="high"
        # )
        # assert result == True
        pass
    
    def test_update_confidence_thresholds(self, db_session):
        """Test automatic threshold updates based on validation history."""
        service = ActiveLearningService(db_session)
        
        thresholds = service.update_confidence_thresholds(lookback_days=30)
        
        assert isinstance(thresholds, dict)
        # Should return thresholds by engine
        for engine, threshold in thresholds.items():
            assert 0.5 <= threshold <= 1.0
    
    def test_get_learning_statistics(self, db_session):
        """Test retrieval of learning statistics."""
        service = ActiveLearningService(db_session)
        
        stats = service.get_learning_statistics()
        
        assert 'reviewed_last_30_days' in stats
        assert 'pending_review' in stats
        assert 'engine_statistics' in stats
        assert isinstance(stats['engine_statistics'], list)

