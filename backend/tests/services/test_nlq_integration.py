"""
Unit Tests for Integrated NLQ Service

Tests the integration between SemanticCacheService (Component A) and
NaturalLanguageQueryService (Component B).
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.services.nlq_service_integrated import IntegratedNLQService
from app.services.semantic_cache_service import SemanticCacheService
from app.services.nlq_service import NaturalLanguageQueryService


class TestIntegratedNLQService:
    """Test suite for integrated NLQ service"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_cache_service(self):
        """Mock semantic cache service (Component A)"""
        cache = Mock(spec=SemanticCacheService)
        cache.find_similar_query = Mock(return_value=None)
        cache.store_query_with_embedding = Mock(return_value={"success": True})
        cache.get_cache_statistics = Mock(return_value={
            "total_queries": 100,
            "cached_queries": 30,
            "hit_rate": 0.30
        })
        return cache
    
    @pytest.fixture
    def mock_nlq_service(self):
        """Mock NLQ service (Component B)"""
        nlq = Mock(spec=NaturalLanguageQueryService)
        nlq.query = Mock(return_value={
            "success": True,
            "question": "What was NOI?",
            "answer": "The NOI was $1.2M",
            "data": [],
            "query_id": 123
        })
        return nlq
    
    @pytest.fixture
    def integrated_service(self, mock_db, mock_cache_service, mock_nlq_service):
        """Create integrated service with mocked components"""
        with patch('app.services.nlq_service_integrated.SemanticCacheService', return_value=mock_cache_service), \
             patch('app.services.nlq_service_integrated.NaturalLanguageQueryService', return_value=mock_nlq_service):
            service = IntegratedNLQService(mock_db)
            return service
    
    def test_cache_hit_skips_component_b(self, integrated_service, mock_cache_service, mock_nlq_service):
        """
        Test that cache hit skips Component B
        
        Requirement 2: If Component A returns cached result, skip Component B
        """
        # Setup: Component A returns cached result
        cached_result = {
            "id": 100,
            "question": "What was NOI?",
            "answer": "The NOI was $1.2M (cached)",
            "similarity": 0.95
        }
        mock_cache_service.find_similar_query.return_value = cached_result
        
        # Execute
        result = integrated_service.query(
            question="What was NOI?",
            user_id=1
        )
        
        # Verify: Component A was called
        mock_cache_service.find_similar_query.assert_called_once_with(
            question="What was NOI?",
            user_id=1
        )
        
        # Verify: Component B was NOT called (skipped)
        mock_nlq_service.query.assert_not_called()
        
        # Verify: Result is from cache
        assert result['from_cache'] is True
        assert result['answer'] == "The NOI was $1.2M (cached)"
        assert result.get('cache_similarity') is not None
    
    def test_cache_miss_calls_component_b(self, integrated_service, mock_cache_service, mock_nlq_service):
        """
        Test that cache miss calls Component B
        
        Requirement 1: Component A should be called before Component B
        """
        # Setup: Component A returns None (cache miss)
        mock_cache_service.find_similar_query.return_value = None
        
        # Execute
        result = integrated_service.query(
            question="What was NOI?",
            user_id=1
        )
        
        # Verify: Component A was called first
        mock_cache_service.find_similar_query.assert_called_once_with(
            question="What was NOI?",
            user_id=1
        )
        
        # Verify: Component B was called after cache miss
        mock_nlq_service.query.assert_called_once_with(
            question="What was NOI?",
            user_id=1,
            context=None
        )
        
        # Verify: Result is from Component B
        assert result['from_cache'] is False
        assert result['answer'] == "The NOI was $1.2M"
    
    def test_cache_update_on_new_query(self, integrated_service, mock_cache_service, mock_nlq_service):
        """
        Test that Component B updates Component A cache on new queries
        
        Requirement 3: Component B should update Component A cache on new queries
        """
        # Setup: Cache miss
        mock_cache_service.find_similar_query.return_value = None
        mock_nlq_service.query.return_value = {
            "success": True,
            "question": "What was NOI?",
            "answer": "The NOI was $1.2M",
            "query_id": 123
        }
        
        # Execute
        result = integrated_service.query(
            question="What was NOI?",
            user_id=1
        )
        
        # Verify: Cache was updated with new query
        mock_cache_service.store_query_with_embedding.assert_called_once_with(
            query_id=123,
            question="What was NOI?",
            force_regenerate=False
        )
    
    def test_graceful_degradation_on_cache_error(self, mock_db, mock_nlq_service):
        """
        Test graceful degradation when Component A fails
        
        Requirement 4: Error in Component A should not block Component B
        """
        # Setup: Component A raises exception
        with patch('app.services.nlq_service_integrated.SemanticCacheService') as MockCache:
            MockCache.side_effect = Exception("Cache service unavailable")
            
            with patch('app.services.nlq_service_integrated.NaturalLanguageQueryService', return_value=mock_nlq_service):
                service = IntegratedNLQService(mock_db)
                
                # Execute: Should still work without cache
                result = service.query(
                    question="What was NOI?",
                    user_id=1
                )
                
                # Verify: Component B was called despite cache error
                mock_nlq_service.query.assert_called_once()
                
                # Verify: Result is successful
                assert result['success'] is True
                assert result['from_cache'] is False
    
    def test_cache_error_does_not_block_query(self, integrated_service, mock_cache_service, mock_nlq_service):
        """
        Test that cache lookup error doesn't block Component B
        """
        # Setup: Component A raises exception during lookup
        mock_cache_service.find_similar_query.side_effect = Exception("Database connection error")
        
        # Execute
        result = integrated_service.query(
            question="What was NOI?",
            user_id=1
        )
        
        # Verify: Component B was still called
        mock_nlq_service.query.assert_called_once()
        
        # Verify: Result is successful
        assert result['success'] is True
        assert result['from_cache'] is False
    
    def test_cache_update_error_does_not_break_query(self, integrated_service, mock_cache_service, mock_nlq_service):
        """
        Test that cache update error doesn't break the query
        """
        # Setup: Cache miss, but update fails
        mock_cache_service.find_similar_query.return_value = None
        mock_cache_service.store_query_with_embedding.side_effect = Exception("Update failed")
        
        # Execute
        result = integrated_service.query(
            question="What was NOI?",
            user_id=1
        )
        
        # Verify: Query still succeeds
        assert result['success'] is True
        assert result['from_cache'] is False
    
    def test_metrics_on_cache_hit(self, integrated_service, mock_cache_service):
        """
        Test metrics are recorded on cache hit
        
        Requirement 5: Add metrics for cache hit/miss rate
        """
        # Setup: Cache hit
        cached_result = {
            "id": 100,
            "question": "What was NOI?",
            "answer": "The NOI was $1.2M",
            "similarity": 0.95
        }
        mock_cache_service.find_similar_query.return_value = cached_result
        
        # Execute
        result = integrated_service.query(
            question="What was NOI?",
            user_id=1
        )
        
        # Verify: Statistics updated
        stats = integrated_service.get_cache_statistics()
        assert stats['integration_stats']['cache_hits'] == 1
        assert stats['integration_stats']['cache_misses'] == 0
        assert stats['integration_stats']['hit_rate'] == 1.0
    
    def test_metrics_on_cache_miss(self, integrated_service, mock_cache_service, mock_nlq_service):
        """
        Test metrics are recorded on cache miss
        """
        # Setup: Cache miss
        mock_cache_service.find_similar_query.return_value = None
        
        # Execute
        result = integrated_service.query(
            question="What was NOI?",
            user_id=1
        )
        
        # Verify: Statistics updated
        stats = integrated_service.get_cache_statistics()
        assert stats['integration_stats']['cache_hits'] == 0
        assert stats['integration_stats']['cache_misses'] == 1
        assert stats['integration_stats']['hit_rate'] == 0.0
    
    def test_metrics_on_cache_error(self, integrated_service, mock_cache_service, mock_nlq_service):
        """
        Test metrics are recorded on cache error
        """
        # Setup: Cache error
        mock_cache_service.find_similar_query.side_effect = Exception("Cache error")
        
        # Execute
        result = integrated_service.query(
            question="What was NOI?",
            user_id=1
        )
        
        # Verify: Error counted
        stats = integrated_service.get_cache_statistics()
        assert stats['integration_stats']['cache_errors'] == 1
    
    def test_health_status(self, integrated_service):
        """
        Test health status reporting
        """
        health = integrated_service.get_health_status()
        
        assert 'component_a' in health
        assert 'component_b' in health
        assert 'integration' in health
        assert health['component_a']['name'] == 'SemanticCacheService'
        assert health['component_b']['name'] == 'NaturalLanguageQueryService'
        assert health['integration']['graceful_degradation'] is True
    
    def test_context_passed_to_component_b(self, integrated_service, mock_cache_service, mock_nlq_service):
        """
        Test that context is passed correctly to Component B
        """
        # Setup: Cache miss
        mock_cache_service.find_similar_query.return_value = None
        
        context = {
            'property_id': 1,
            'property_code': 'ESP001',
            'property_name': 'Eastern Shore Plaza'
        }
        
        # Execute
        result = integrated_service.query(
            question="What was NOI?",
            user_id=1,
            context=context
        )
        
        # Verify: Context passed to Component B
        mock_nlq_service.query.assert_called_once_with(
            question="What was NOI?",
            user_id=1,
            context=context
        )
    
    def test_multiple_queries_accumulate_stats(self, integrated_service, mock_cache_service, mock_nlq_service):
        """
        Test that multiple queries accumulate statistics correctly
        """
        # Setup: Alternating cache hits and misses
        mock_cache_service.find_similar_query.side_effect = [
            {"id": 1, "answer": "Cached 1"},  # Hit 1
            None,  # Miss 1
            {"id": 2, "answer": "Cached 2"},  # Hit 2
            None,  # Miss 2
        ]
        
        # Execute 4 queries
        for i in range(4):
            integrated_service.query(
                question=f"Question {i}",
                user_id=1
            )
        
        # Verify: Statistics correct
        stats = integrated_service.get_cache_statistics()
        assert stats['integration_stats']['cache_hits'] == 2
        assert stats['integration_stats']['cache_misses'] == 2
        assert stats['integration_stats']['hit_rate'] == 0.5
        assert stats['integration_stats']['total_queries'] == 4

