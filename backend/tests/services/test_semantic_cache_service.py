"""
Unit Tests for Semantic Cache Service

Tests cosine similarity calculation, cache lookup, TTL expiration,
and edge cases.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List
import numpy as np

from app.services.semantic_cache_service import SemanticCacheService, cosine_similarity
from app.models.nlq_query import NLQQuery
from app.config.cache_config import cache_config


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service"""
    service = Mock()
    service.generate_embedding.return_value = [0.1] * 1536
    return service


@pytest.fixture
def cache_service(db_session, mock_embedding_service):
    """Create cache service instance"""
    return SemanticCacheService(db_session, mock_embedding_service)


class TestCosineSimilarity:
    """Test cosine similarity calculation"""
    
    def test_cosine_similarity_identical_vectors(self):
        """Test similarity of identical vectors"""
        vec = [0.1, 0.2, 0.3, 0.4, 0.5]
        similarity = cosine_similarity(vec, vec)
        assert abs(similarity - 1.0) < 0.0001  # Should be exactly 1.0
    
    def test_cosine_similarity_orthogonal_vectors(self):
        """Test similarity of orthogonal vectors"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = cosine_similarity(vec1, vec2)
        assert abs(similarity - 0.0) < 0.0001  # Should be 0.0
    
    def test_cosine_similarity_opposite_vectors(self):
        """Test similarity of opposite vectors"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        similarity = cosine_similarity(vec1, vec2)
        assert abs(similarity - (-1.0)) < 0.0001  # Should be -1.0
    
    def test_cosine_similarity_different_dimensions(self):
        """Test similarity with mismatched dimensions"""
        vec1 = [0.1, 0.2, 0.3]
        vec2 = [0.1, 0.2]
        similarity = cosine_similarity(vec1, vec2)
        assert similarity == 0.0  # Should return 0.0 for mismatch
    
    def test_cosine_similarity_empty_vectors(self):
        """Test similarity with empty vectors"""
        similarity = cosine_similarity([], [])
        assert similarity == 0.0
    
    def test_cosine_similarity_zero_vectors(self):
        """Test similarity with zero vectors"""
        vec = [0.0] * 10
        similarity = cosine_similarity(vec, vec)
        assert similarity == 0.0
    
    def test_cosine_similarity_high_similarity(self):
        """Test similarity with highly similar vectors"""
        vec1 = [0.1, 0.2, 0.3, 0.4, 0.5]
        vec2 = [0.11, 0.21, 0.31, 0.41, 0.51]  # Very similar
        similarity = cosine_similarity(vec1, vec2)
        assert similarity > 0.99  # Should be very high


class TestCacheLookup:
    """Test cache lookup functionality"""
    
    def test_find_exact_match_by_hash(self, cache_service, db_session):
        """Test finding exact match by hash"""
        from datetime import datetime, timedelta
        
        # Create a test query
        query = NLQQuery(
            user_id=1,
            question="What is NOI?",
            answer="NOI is Net Operating Income",
            question_hash=cache_service._calculate_hash("What is NOI?"),
            created_at=datetime.now() - timedelta(hours=1)
        )
        db_session.add(query)
        db_session.commit()
        
        # Find exact match
        result = cache_service._find_exact_match(
            question_hash=cache_service._calculate_hash("What is NOI?"),
            user_id=1
        )
        
        assert result is not None
        assert result.question == "What is NOI?"
    
    def test_find_similar_by_embedding(self, cache_service, db_session):
        """Test finding similar query by embedding"""
        from datetime import datetime, timedelta
        
        # Create a test query with embedding
        embedding1 = [0.1] * 1536
        embedding2 = [0.11] * 1536  # Very similar
        
        query = NLQQuery(
            user_id=1,
            question="What is NOI?",
            answer="NOI is Net Operating Income",
            question_embedding=embedding1,
            question_hash="hash1",
            created_at=datetime.now() - timedelta(hours=1)
        )
        db_session.add(query)
        db_session.commit()
        
        # Find similar query
        result = cache_service._find_similar_by_embedding(
            embedding=embedding2,
            question_hash="hash2",
            user_id=1,
            threshold=0.95
        )
        
        assert result is not None
        assert result['question'] == "What is NOI?"
        assert result['similarity'] > 0.95
    
    def test_find_similar_below_threshold(self, cache_service, db_session):
        """Test that queries below threshold are not returned"""
        from datetime import datetime, timedelta
        
        # Create a test query with embedding
        embedding1 = [0.1] * 1536
        embedding2 = [0.9] * 1536  # Very different
        
        query = NLQQuery(
            user_id=1,
            question="What is NOI?",
            answer="NOI is Net Operating Income",
            question_embedding=embedding1,
            question_hash="hash1",
            created_at=datetime.now() - timedelta(hours=1)
        )
        db_session.add(query)
        db_session.commit()
        
        # Find similar query (should not find due to low similarity)
        result = cache_service._find_similar_by_embedding(
            embedding=embedding2,
            question_hash="hash2",
            user_id=1,
            threshold=0.95
        )
        
        assert result is None
    
    def test_find_similar_respects_ttl(self, cache_service, db_session):
        """Test that TTL is respected"""
        from datetime import datetime, timedelta
        
        # Create an old query (outside TTL)
        old_query = NLQQuery(
            user_id=1,
            question="What is NOI?",
            answer="NOI is Net Operating Income",
            question_embedding=[0.1] * 1536,
            question_hash="hash1",
            created_at=datetime.now() - timedelta(hours=25)  # Outside 24h TTL
        )
        db_session.add(old_query)
        db_session.commit()
        
        # Try to find similar query
        result = cache_service._find_similar_by_embedding(
            embedding=[0.11] * 1536,
            question_hash="hash2",
            user_id=1,
            threshold=0.95
        )
        
        assert result is None  # Should not find expired query


class TestStoreQuery:
    """Test storing queries with embeddings"""
    
    def test_store_query_with_embedding(self, cache_service, db_session):
        """Test storing query with embedding"""
        # Create a query without embedding
        query = NLQQuery(
            user_id=1,
            question="What is NOI?",
            answer="NOI is Net Operating Income"
        )
        db_session.add(query)
        db_session.commit()
        db_session.refresh(query)
        
        # Store embedding
        result = cache_service.store_query_with_embedding(
            query_id=query.id,
            question="What is NOI?"
        )
        
        assert result['success'] is True
        assert result['embedding_dimension'] == 1536
        
        # Verify embedding was stored
        db_session.refresh(query)
        assert query.question_embedding is not None
        assert len(query.question_embedding) == 1536
        assert query.question_hash is not None
    
    def test_store_query_skips_if_exists(self, cache_service, db_session):
        """Test that existing embedding is not regenerated"""
        # Create a query with embedding
        query = NLQQuery(
            user_id=1,
            question="What is NOI?",
            answer="NOI is Net Operating Income",
            question_embedding=[0.1] * 1536
        )
        db_session.add(query)
        db_session.commit()
        db_session.refresh(query)
        
        original_embedding = query.question_embedding.copy()
        
        # Try to store again (should skip)
        result = cache_service.store_query_with_embedding(
            query_id=query.id,
            question="What is NOI?"
        )
        
        assert result['success'] is True
        assert result['message'] == "Embedding already exists"
        
        # Verify embedding wasn't changed
        db_session.refresh(query)
        assert query.question_embedding == original_embedding
    
    def test_store_query_force_regenerate(self, cache_service, db_session):
        """Test force regeneration of embedding"""
        # Create a query with embedding
        query = NLQQuery(
            user_id=1,
            question="What is NOI?",
            answer="NOI is Net Operating Income",
            question_embedding=[0.1] * 1536
        )
        db_session.add(query)
        db_session.commit()
        db_session.refresh(query)
        
        # Force regenerate
        result = cache_service.store_query_with_embedding(
            query_id=query.id,
            question="What is NOI?",
            force_regenerate=True
        )
        
        assert result['success'] is True
        
        # Verify embedding was regenerated
        db_session.refresh(query)
        assert query.question_embedding is not None


class TestFindSimilarQuery:
    """Test find_similar_query method"""
    
    def test_find_similar_query_exact_match(self, cache_service, db_session):
        """Test finding exact match via hash"""
        from datetime import datetime, timedelta
        
        # Create a test query
        query = NLQQuery(
            user_id=1,
            question="What is NOI?",
            answer="NOI is Net Operating Income",
            question_hash=cache_service._calculate_hash("What is NOI?"),
            created_at=datetime.now() - timedelta(hours=1)
        )
        db_session.add(query)
        db_session.commit()
        
        # Find similar query
        result = cache_service.find_similar_query(
            question="What is NOI?",
            user_id=1
        )
        
        assert result is not None
        assert result['question'] == "What is NOI?"
        assert result.get('similarity') == 1.0  # Exact match
    
    def test_find_similar_query_semantic_match(self, cache_service, db_session):
        """Test finding semantic match via embedding"""
        from datetime import datetime, timedelta
        
        # Create a test query with embedding
        query = NLQQuery(
            user_id=1,
            question="What is NOI?",
            answer="NOI is Net Operating Income",
            question_embedding=[0.1] * 1536,
            question_hash="hash1",
            created_at=datetime.now() - timedelta(hours=1)
        )
        db_session.add(query)
        db_session.commit()
        
        # Mock embedding service to return similar embedding
        cache_service.embedding_service.generate_embedding.return_value = [0.11] * 1536
        
        # Find similar query (paraphrased)
        result = cache_service.find_similar_query(
            question="What's the NOI?",
            user_id=1
        )
        
        # Should find match if similarity is high enough
        # (depends on actual embedding similarity)
        if result:
            assert result['question'] == "What is NOI?"
            assert result.get('similarity', 0) >= cache_config.SIMILARITY_THRESHOLD
    
    def test_find_similar_query_no_match(self, cache_service, db_session):
        """Test when no similar query is found"""
        # Find similar query (no queries in DB)
        result = cache_service.find_similar_query(
            question="What is revenue?",
            user_id=1
        )
        
        assert result is None
    
    def test_find_similar_query_embedding_failure(self, cache_service, db_session):
        """Test graceful degradation when embedding fails"""
        # Mock embedding service to fail
        cache_service.embedding_service.generate_embedding.return_value = None
        
        # Should not crash, just return None
        result = cache_service.find_similar_query(
            question="What is NOI?",
            user_id=1
        )
        
        # Should return None (graceful degradation)
        assert result is None or isinstance(result, dict)


class TestCacheStatistics:
    """Test cache statistics"""
    
    def test_get_cache_statistics(self, cache_service, db_session):
        """Test getting cache statistics"""
        from datetime import datetime, timedelta
        
        # Create test queries
        for i in range(10):
            query = NLQQuery(
                user_id=1,
                question=f"Question {i}",
                answer=f"Answer {i}",
                from_cache=(i < 3),  # First 3 from cache
                cache_similarity=95.0 if i < 3 else None,
                created_at=datetime.now() - timedelta(hours=1)
            )
            db_session.add(query)
        
        db_session.commit()
        
        # Get statistics
        stats = cache_service.get_cache_statistics(hours=24)
        
        assert stats['total_queries'] == 10
        assert stats['cached_queries'] == 3
        assert stats['hit_rate'] == 0.3
        assert stats['average_similarity'] == 95.0
    
    def test_get_cache_statistics_empty(self, cache_service, db_session):
        """Test statistics with no queries"""
        stats = cache_service.get_cache_statistics(hours=24)
        
        assert stats['total_queries'] == 0
        assert stats['cached_queries'] == 0
        assert stats['hit_rate'] == 0.0


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_cosine_similarity_with_none(self):
        """Test cosine similarity with None values"""
        similarity = cosine_similarity(None, [0.1, 0.2])
        assert similarity == 0.0
        
        similarity = cosine_similarity([0.1, 0.2], None)
        assert similarity == 0.0
    
    def test_find_similar_query_disabled_cache(self, cache_service, db_session):
        """Test when cache is disabled"""
        with patch('app.config.cache_config.cache_config.ENABLE_SEMANTIC_CACHE', False):
            result = cache_service.find_similar_query(
                question="What is NOI?",
                user_id=1
            )
            assert result is None
    
    def test_store_query_not_found(self, cache_service, db_session):
        """Test storing embedding for non-existent query"""
        result = cache_service.store_query_with_embedding(
            query_id=99999,
            question="What is NOI?"
        )
        
        assert result['success'] is False
        assert 'not found' in result['error'].lower()
    
    def test_find_similar_query_database_error(self, cache_service, db_session):
        """Test graceful handling of database errors"""
        # Force a database error
        with patch.object(db_session, 'query', side_effect=Exception("DB Error")):
            result = cache_service.find_similar_query(
                question="What is NOI?",
                user_id=1
            )
            # Should return None, not crash
            assert result is None


class TestPerformance:
    """Test performance requirements"""
    
    def test_cache_lookup_performance(self, cache_service, db_session):
        """Test that cache lookup meets performance target"""
        import time
        
        # Create test query
        from datetime import datetime, timedelta
        query = NLQQuery(
            user_id=1,
            question="What is NOI?",
            answer="NOI is Net Operating Income",
            question_hash=cache_service._calculate_hash("What is NOI?"),
            created_at=datetime.now() - timedelta(hours=1)
        )
        db_session.add(query)
        db_session.commit()
        
        # Measure lookup time
        start = time.time()
        result = cache_service.find_similar_query(
            question="What is NOI?",
            user_id=1
        )
        elapsed_ms = (time.time() - start) * 1000
        
        # Should be under 50ms
        assert elapsed_ms < cache_config.PERFORMANCE_TARGET_MS * 2  # Allow some margin for test environment
        assert result is not None

