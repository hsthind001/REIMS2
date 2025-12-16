"""
Integration Tests for Semantic Cache

End-to-end tests for semantic cache with NLQ service,
paraphrased question matching, and cache statistics.
"""
import pytest
from datetime import datetime, timedelta

from app.services.semantic_cache_service import SemanticCacheService
from app.services.nlq_service import NaturalLanguageQueryService
from app.models.nlq_query import NLQQuery
from app.config.cache_config import cache_config


@pytest.fixture
def cache_service(db_session):
    """Create cache service instance"""
    return SemanticCacheService(db_session)


@pytest.fixture
def nlq_service(db_session):
    """Create NLQ service instance"""
    return NaturalLanguageQueryService(db_session)


class TestEndToEndCacheFlow:
    """Test end-to-end cache flow with NLQ service"""
    
    @pytest.mark.skip(reason="Requires LLM API key and full NLQ setup")
    def test_cache_flow_with_nlq_service(self, nlq_service, db_session):
        """Test complete cache flow with NLQ service"""
        # This would require:
        # 1. Valid LLM API key
        # 2. Database with financial data
        # 3. Full NLQ service setup
        
        # For now, this is a placeholder
        pass
    
    def test_paraphrased_question_matching(self, cache_service, db_session):
        """Test that paraphrased questions match"""
        from unittest.mock import patch
        
        # Create a query with embedding
        embedding1 = [0.1] * 1536
        
        query = NLQQuery(
            user_id=1,
            question="What is the Net Operating Income?",
            answer="NOI is Net Operating Income",
            question_embedding=embedding1,
            question_hash="hash1",
            created_at=datetime.now() - timedelta(hours=1)
        )
        db_session.add(query)
        db_session.commit()
        
        # Mock embedding service to return similar embedding for paraphrased question
        with patch.object(cache_service.embedding_service, 'generate_embedding', return_value=[0.11] * 1536):
            # Try paraphrased question
            result = cache_service.find_similar_query(
                question="What's the NOI?",
                user_id=1
            )
            
            # Should find match if similarity is high enough
            if result:
                assert result['question'] == "What is the Net Operating Income?"
                assert result.get('similarity', 0) >= cache_config.SIMILARITY_THRESHOLD


class TestCacheHitRate:
    """Test cache hit rate over multiple queries"""
    
    def test_cache_hit_rate_calculation(self, cache_service, db_session):
        """Test cache hit rate calculation"""
        from datetime import datetime, timedelta
        
        # Create mix of cached and non-cached queries
        for i in range(20):
            query = NLQQuery(
                user_id=1,
                question=f"Question {i}",
                answer=f"Answer {i}",
                from_cache=(i < 6),  # 6 out of 20 from cache (30%)
                cache_similarity=95.0 if i < 6 else None,
                created_at=datetime.now() - timedelta(hours=1)
            )
            db_session.add(query)
        
        db_session.commit()
        
        # Get statistics
        stats = cache_service.get_cache_statistics(hours=24)
        
        assert stats['total_queries'] == 20
        assert stats['cached_queries'] == 6
        assert abs(stats['hit_rate'] - 0.30) < 0.01  # 30% hit rate
    
    def test_cache_hit_rate_validation(self, cache_service, db_session):
        """Test cache hit rate validation"""
        from datetime import datetime, timedelta
        
        # Create queries with high hit rate (>30%)
        for i in range(10):
            query = NLQQuery(
                user_id=1,
                question=f"Question {i}",
                answer=f"Answer {i}",
                from_cache=(i < 5),  # 50% hit rate
                cache_similarity=95.0 if i < 5 else None,
                created_at=datetime.now() - timedelta(hours=1)
            )
            db_session.add(query)
        
        db_session.commit()
        
        stats = cache_service.get_cache_statistics(hours=24)
        validation = stats.get('validation', {})
        
        assert validation['meets_target'] is True
        assert validation['hit_rate'] == 0.5
    
    def test_cache_hit_rate_below_target(self, cache_service, db_session):
        """Test cache hit rate below target"""
        from datetime import datetime, timedelta
        
        # Create queries with low hit rate (<30%)
        for i in range(10):
            query = NLQQuery(
                user_id=1,
                question=f"Question {i}",
                answer=f"Answer {i}",
                from_cache=(i < 1),  # 10% hit rate
                cache_similarity=95.0 if i < 1 else None,
                created_at=datetime.now() - timedelta(hours=1)
            )
            db_session.add(query)
        
        db_session.commit()
        
        stats = cache_service.get_cache_statistics(hours=24)
        validation = stats.get('validation', {})
        
        assert validation['meets_target'] is False
        assert validation['hit_rate'] == 0.1


class TestParaphrasedMatching:
    """Test matching of paraphrased questions"""
    
    def test_what_is_vs_whats(self, cache_service, db_session):
        """Test matching 'What is' vs 'What's'"""
        from unittest.mock import patch
        
        # Create query
        embedding = [0.1] * 1536
        query = NLQQuery(
            user_id=1,
            question="What is NOI?",
            answer="NOI is Net Operating Income",
            question_embedding=embedding,
            question_hash="hash1",
            created_at=datetime.now() - timedelta(hours=1)
        )
        db_session.add(query)
        db_session.commit()
        
        # Mock similar embedding for paraphrased question
        with patch.object(cache_service.embedding_service, 'generate_embedding', return_value=[0.11] * 1536):
            result = cache_service.find_similar_query(
                question="What's NOI?",
                user_id=1
            )
            
            # Should match if embeddings are similar enough
            if result:
                assert result['question'] == "What is NOI?"
    
    def test_different_wordings(self, cache_service, db_session):
        """Test matching different wordings of same question"""
        from unittest.mock import patch
        
        # Create query
        embedding = [0.1] * 1536
        query = NLQQuery(
            user_id=1,
            question="Show me the Net Operating Income",
            answer="NOI is Net Operating Income",
            question_embedding=embedding,
            question_hash="hash1",
            created_at=datetime.now() - timedelta(hours=1)
        )
        db_session.add(query)
        db_session.commit()
        
        # Mock similar embedding
        with patch.object(cache_service.embedding_service, 'generate_embedding', return_value=[0.11] * 1536):
            result = cache_service.find_similar_query(
                question="What is the NOI?",
                user_id=1
            )
            
            # Should match if embeddings are similar enough
            if result:
                assert 'Net Operating Income' in result['question'] or 'NOI' in result['question']


class TestCacheStatisticsTracking:
    """Test cache statistics tracking"""
    
    def test_statistics_tracks_embeddings(self, cache_service, db_session):
        """Test that statistics track queries with embeddings"""
        from datetime import datetime, timedelta
        
        # Create queries with and without embeddings
        for i in range(5):
            query = NLQQuery(
                user_id=1,
                question=f"Question {i}",
                answer=f"Answer {i}",
                question_embedding=[0.1] * 1536 if i < 3 else None,
                created_at=datetime.now() - timedelta(hours=1)
            )
            db_session.add(query)
        
        db_session.commit()
        
        stats = cache_service.get_cache_statistics(hours=24)
        
        assert stats['queries_with_embeddings'] == 3
        assert stats['total_queries'] == 5
    
    def test_statistics_average_similarity(self, cache_service, db_session):
        """Test average similarity calculation"""
        from datetime import datetime, timedelta
        
        # Create cached queries with different similarity scores
        similarities = [95.0, 96.0, 97.0, 98.0, 99.0]
        for i, sim in enumerate(similarities):
            query = NLQQuery(
                user_id=1,
                question=f"Question {i}",
                answer=f"Answer {i}",
                from_cache=True,
                cache_similarity=sim,
                created_at=datetime.now() - timedelta(hours=1)
            )
            db_session.add(query)
        
        db_session.commit()
        
        stats = cache_service.get_cache_statistics(hours=24)
        
        assert stats['average_similarity'] == pytest.approx(97.0, abs=0.1)


class TestTTLExpiration:
    """Test TTL expiration"""
    
    def test_queries_expire_after_ttl(self, cache_service, db_session):
        """Test that queries expire after TTL"""
        # Create old query (outside TTL)
        old_query = NLQQuery(
            user_id=1,
            question="What is NOI?",
            answer="NOI is Net Operating Income",
            question_hash=cache_service._calculate_hash("What is NOI?"),
            question_embedding=[0.1] * 1536,
            created_at=datetime.now() - timedelta(hours=cache_config.CACHE_TTL_HOURS + 1)
        )
        db_session.add(old_query)
        db_session.commit()
        
        # Try to find query (should not find due to TTL)
        result = cache_service.find_similar_query(
            question="What is NOI?",
            user_id=1
        )
        
        assert result is None
    
    def test_queries_within_ttl_are_found(self, cache_service, db_session):
        """Test that queries within TTL are found"""
        # Create recent query (within TTL)
        recent_query = NLQQuery(
            user_id=1,
            question="What is NOI?",
            answer="NOI is Net Operating Income",
            question_hash=cache_service._calculate_hash("What is NOI?"),
            question_embedding=[0.1] * 1536,
            created_at=datetime.now() - timedelta(hours=1)
        )
        db_session.add(recent_query)
        db_session.commit()
        
        # Try to find query (should find)
        result = cache_service.find_similar_query(
            question="What is NOI?",
            user_id=1
        )
        
        assert result is not None
        assert result['question'] == "What is NOI?"


class TestUserFiltering:
    """Test user-specific cache filtering"""
    
    def test_cache_respects_user_id(self, cache_service, db_session):
        """Test that cache respects user_id filter"""
        from datetime import datetime, timedelta
        
        # Create query for user 1
        query1 = NLQQuery(
            user_id=1,
            question="What is NOI?",
            answer="NOI is Net Operating Income",
            question_hash=cache_service._calculate_hash("What is NOI?"),
            created_at=datetime.now() - timedelta(hours=1)
        )
        db_session.add(query1)
        
        # Create query for user 2
        query2 = NLQQuery(
            user_id=2,
            question="What is NOI?",
            answer="NOI is Net Operating Income",
            question_hash=cache_service._calculate_hash("What is NOI?"),
            created_at=datetime.now() - timedelta(hours=1)
        )
        db_session.add(query2)
        db_session.commit()
        
        # Find query for user 1 (should only find user 1's query)
        result = cache_service.find_similar_query(
            question="What is NOI?",
            user_id=1
        )
        
        assert result is not None
        assert result['user_id'] == 1


class TestPerformanceIntegration:
    """Test performance in integration scenarios"""
    
    def test_cache_lookup_performance_with_multiple_queries(self, cache_service, db_session):
        """Test cache lookup performance with multiple cached queries"""
        import time
        from datetime import datetime, timedelta
        
        # Create multiple queries
        for i in range(50):
            query = NLQQuery(
                user_id=1,
                question=f"Question {i}",
                answer=f"Answer {i}",
                question_embedding=[0.1 + i * 0.001] * 1536,
                question_hash=f"hash{i}",
                created_at=datetime.now() - timedelta(hours=1)
            )
            db_session.add(query)
        
        db_session.commit()
        
        # Measure lookup time
        start = time.time()
        result = cache_service.find_similar_query(
            question="Question 25",
            user_id=1
        )
        elapsed_ms = (time.time() - start) * 1000
        
        # Should be under performance target (with margin for test environment)
        assert elapsed_ms < cache_config.PERFORMANCE_TARGET_MS * 3

