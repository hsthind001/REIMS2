"""
Unit Tests for Reranker Service

Tests Cohere API integration, fallback reranking, error handling,
and precision improvement.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.reranker_service import RerankerService
from app.config.reranker_config import reranker_config


@pytest.fixture
def mock_cohere_client():
    """Mock Cohere client"""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.results = [
        MagicMock(index=1, relevance_score=0.95),
        MagicMock(index=0, relevance_score=0.85),
        MagicMock(index=2, relevance_score=0.75),
    ]
    mock_client.rerank.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_fallback_model():
    """Mock sentence-transformers CrossEncoder"""
    mock_model = MagicMock()
    mock_model.predict.return_value = [0.9, 0.8, 0.7]
    return mock_model


@pytest.fixture
def sample_candidates():
    """Sample candidate results for testing"""
    return [
        {'chunk_id': 1, 'chunk_text': 'DSCR is 1.20, below threshold', 'similarity': 0.9},
        {'chunk_id': 2, 'chunk_text': 'Debt service coverage analysis', 'similarity': 0.8},
        {'chunk_id': 3, 'chunk_text': 'Financial metrics discussion', 'similarity': 0.7},
    ]


class TestCohereReranking:
    """Test Cohere API reranking"""
    
    @patch('app.services.reranker_service.cohere')
    @patch('app.config.reranker_config.reranker_config.COHERE_API_KEY', 'test-key')
    def test_rerank_with_cohere(self, mock_cohere, mock_cohere_client, sample_candidates):
        """Test reranking using Cohere API"""
        mock_cohere.Client.return_value = mock_cohere_client
        
        service = RerankerService()
        service.cohere_client = mock_cohere_client
        service.use_cohere = True
        
        query = "DSCR below 1.25"
        reranked = service._rerank_with_cohere(query, sample_candidates, top_k=3)
        
        assert len(reranked) == 3
        assert all('rerank_score' in r for r in reranked)
        assert all('rerank_rank' in r for r in reranked)
        assert all(r['rerank_method'] == 'cohere' for r in reranked)
        
        # Results should be sorted by rerank_score (descending)
        scores = [r['rerank_score'] for r in reranked]
        assert scores == sorted(scores, reverse=True)
        
        # Verify Cohere API was called
        mock_cohere_client.rerank.assert_called_once()
        call_args = mock_cohere_client.rerank.call_args
        assert call_args[1]['query'] == query
        assert call_args[1]['top_n'] == 3
    
    @patch('app.services.reranker_service.cohere')
    @patch('app.config.reranker_config.reranker_config.COHERE_API_KEY', 'test-key')
    def test_cohere_rerank_preserves_metadata(self, mock_cohere, mock_cohere_client, sample_candidates):
        """Test that Cohere reranking preserves original metadata"""
        mock_cohere.Client.return_value = mock_cohere_client
        
        service = RerankerService()
        service.cohere_client = mock_cohere_client
        service.use_cohere = True
        
        # Add metadata to candidates
        sample_candidates[0]['property_id'] = 1
        sample_candidates[0]['document_type'] = 'income_statement'
        
        query = "DSCR"
        reranked = service._rerank_with_cohere(query, sample_candidates, top_k=3)
        
        # Metadata should be preserved
        assert 'property_id' in reranked[0]
        assert 'document_type' in reranked[0]
        assert reranked[0]['property_id'] == 1


class TestFallbackReranking:
    """Test sentence-transformers fallback reranking"""
    
    @patch('app.services.reranker_service.CrossEncoder')
    def test_rerank_with_fallback(self, mock_cross_encoder, mock_fallback_model, sample_candidates):
        """Test reranking using fallback model"""
        mock_cross_encoder.return_value = mock_fallback_model
        
        service = RerankerService()
        service.fallback_model = mock_fallback_model
        service.use_fallback = True
        
        query = "DSCR below 1.25"
        reranked = service._rerank_with_fallback(query, sample_candidates, top_k=3)
        
        assert len(reranked) == 3
        assert all('rerank_score' in r for r in reranked)
        assert all('rerank_rank' in r for r in reranked)
        assert all(r['rerank_method'] == 'sentence-transformers' for r in reranked)
        
        # Results should be sorted by rerank_score (descending)
        scores = [r['rerank_score'] for r in reranked]
        assert scores == sorted(scores, reverse=True)
        
        # Verify model was called
        mock_fallback_model.predict.assert_called_once()
    
    @patch('app.services.reranker_service.CrossEncoder')
    def test_fallback_rerank_preserves_metadata(self, mock_cross_encoder, mock_fallback_model, sample_candidates):
        """Test that fallback reranking preserves original metadata"""
        mock_cross_encoder.return_value = mock_fallback_model
        
        service = RerankerService()
        service.fallback_model = mock_fallback_model
        service.use_fallback = True
        
        # Add metadata
        sample_candidates[0]['property_id'] = 1
        
        query = "DSCR"
        reranked = service._rerank_with_fallback(query, sample_candidates, top_k=3)
        
        # Metadata should be preserved
        assert 'property_id' in reranked[0]


class TestRerankMethod:
    """Test main rerank method"""
    
    @patch('app.services.reranker_service.cohere')
    @patch('app.config.reranker_config.reranker_config.COHERE_API_KEY', 'test-key')
    def test_rerank_uses_cohere_when_available(self, mock_cohere, mock_cohere_client, sample_candidates):
        """Test that rerank uses Cohere when available"""
        mock_cohere.Client.return_value = mock_cohere_client
        
        service = RerankerService()
        service.cohere_client = mock_cohere_client
        service.use_cohere = True
        
        query = "DSCR"
        reranked = service.rerank(query, sample_candidates, top_k=3)
        
        assert len(reranked) == 3
        assert all(r['rerank_method'] == 'cohere' for r in reranked)
        mock_cohere_client.rerank.assert_called_once()
    
    @patch('app.services.reranker_service.CrossEncoder')
    def test_rerank_falls_back_when_cohere_unavailable(self, mock_cross_encoder, mock_fallback_model, sample_candidates):
        """Test that rerank falls back to sentence-transformers when Cohere unavailable"""
        mock_cross_encoder.return_value = mock_fallback_model
        
        service = RerankerService()
        service.use_cohere = False
        service.fallback_model = mock_fallback_model
        service.use_fallback = True
        
        query = "DSCR"
        reranked = service.rerank(query, sample_candidates, top_k=3)
        
        assert len(reranked) == 3
        assert all(r['rerank_method'] == 'sentence-transformers' for r in reranked)
        mock_fallback_model.predict.assert_called_once()
    
    @patch('app.config.reranker_config.reranker_config.RERANK_ENABLED', False)
    def test_rerank_disabled(self, sample_candidates):
        """Test that reranking is skipped when disabled"""
        service = RerankerService()
        
        query = "DSCR"
        reranked = service.rerank(query, sample_candidates, top_k=3)
        
        # Should return original results (limited to top_k)
        assert len(reranked) == 3
        assert reranked == sample_candidates[:3]
    
    def test_rerank_empty_candidates(self):
        """Test reranking with empty candidates"""
        service = RerankerService()
        
        query = "DSCR"
        reranked = service.rerank(query, [], top_k=10)
        
        assert reranked == []
    
    @patch('app.services.reranker_service.cohere')
    @patch('app.config.reranker_config.reranker_config.COHERE_API_KEY', 'test-key')
    @patch('app.config.reranker_config.reranker_config.RETURN_ORIGINAL_ON_FAILURE', True)
    def test_rerank_returns_original_on_failure(self, mock_cohere, sample_candidates):
        """Test that rerank returns original results on failure"""
        mock_cohere.Client.side_effect = Exception("API error")
        
        service = RerankerService()
        service.use_cohere = False
        service.use_fallback = False
        
        query = "DSCR"
        reranked = service.rerank(query, sample_candidates, top_k=3)
        
        # Should return original results
        assert len(reranked) == 3
        assert reranked == sample_candidates[:3]
    
    @patch('app.services.reranker_service.cohere')
    @patch('app.config.reranker_config.reranker_config.COHERE_API_KEY', 'test-key')
    def test_rerank_limits_to_top_n(self, mock_cohere, mock_cohere_client):
        """Test that reranking limits candidates to top N"""
        mock_cohere.Client.return_value = mock_cohere_client
        
        # Create many candidates
        many_candidates = [
            {'chunk_id': i, 'chunk_text': f'Text {i}', 'similarity': 0.9 - i * 0.01}
            for i in range(100)
        ]
        
        service = RerankerService()
        service.cohere_client = mock_cohere_client
        service.use_cohere = True
        
        query = "test"
        reranked = service.rerank(query, many_candidates, top_k=10)
        
        # Should only rerank top N candidates
        call_args = mock_cohere_client.rerank.call_args
        documents = call_args[1]['documents']
        assert len(documents) == reranker_config.RERANK_TOP_N  # Should be limited to top N


class TestErrorHandling:
    """Test error handling and retry logic"""
    
    @patch('app.services.reranker_service.cohere')
    @patch('app.config.reranker_config.reranker_config.COHERE_API_KEY', 'test-key')
    @patch('app.config.reranker_config.reranker_config.FALLBACK_ON_ERROR', True)
    def test_cohere_error_falls_back(self, mock_cohere, mock_cohere_client, mock_fallback_model, sample_candidates):
        """Test that Cohere errors trigger fallback"""
        mock_cohere.Client.return_value = mock_cohere_client
        mock_cohere_client.rerank.side_effect = Exception("Cohere API error")
        
        with patch('app.services.reranker_service.CrossEncoder') as mock_ce:
            mock_ce.return_value = mock_fallback_model
            
            service = RerankerService()
            service.cohere_client = mock_cohere_client
            service.use_cohere = True
            service.fallback_model = mock_fallback_model
            service.use_fallback = True
            
            query = "DSCR"
            reranked = service.rerank(query, sample_candidates, top_k=3)
            
            # Should use fallback
            assert len(reranked) == 3
            assert all(r['rerank_method'] == 'sentence-transformers' for r in reranked)
            mock_fallback_model.predict.assert_called_once()
    
    @patch('app.services.reranker_service.cohere')
    @patch('app.config.reranker_config.reranker_config.COHERE_API_KEY', 'test-key')
    @patch('app.config.reranker_config.reranker_config.RETURN_ORIGINAL_ON_FAILURE', True)
    def test_both_methods_fail_returns_original(self, mock_cohere, sample_candidates):
        """Test that when both methods fail, original results are returned"""
        mock_cohere.Client.side_effect = Exception("Cohere init error")
        
        service = RerankerService()
        service.use_cohere = False
        service.use_fallback = False
        
        query = "DSCR"
        reranked = service.rerank(query, sample_candidates, top_k=3)
        
        # Should return original results
        assert len(reranked) == 3
        assert reranked == sample_candidates[:3]


class TestStatus:
    """Test service status"""
    
    def test_get_status(self):
        """Test getting service status"""
        service = RerankerService()
        
        status = service.get_status()
        
        assert 'cohere_available' in status
        assert 'fallback_available' in status
        assert 'reranking_enabled' in status
        assert 'config' in status


class TestPrecisionImprovement:
    """Test precision improvement scenarios"""
    
    @patch('app.services.reranker_service.cohere')
    @patch('app.config.reranker_config.reranker_config.COHERE_API_KEY', 'test-key')
    def test_rerank_improves_ranking(self, mock_cohere, mock_cohere_client):
        """Test that reranking improves result ranking"""
        # Mock Cohere to return better ranking
        mock_response = MagicMock()
        mock_response.results = [
            MagicMock(index=2, relevance_score=0.95),  # Chunk 3 is most relevant
            MagicMock(index=0, relevance_score=0.85),  # Chunk 1 is second
            MagicMock(index=1, relevance_score=0.75),  # Chunk 2 is third
        ]
        mock_cohere_client.rerank.return_value = mock_response
        mock_cohere.Client.return_value = mock_cohere_client
        
        candidates = [
            {'chunk_id': 1, 'chunk_text': 'Less relevant text', 'similarity': 0.9},
            {'chunk_id': 2, 'chunk_text': 'Somewhat relevant', 'similarity': 0.8},
            {'chunk_id': 3, 'chunk_text': 'Most relevant: DSCR below 1.25', 'similarity': 0.7},
        ]
        
        service = RerankerService()
        service.cohere_client = mock_cohere_client
        service.use_cohere = True
        
        query = "DSCR below 1.25"
        reranked = service.rerank(query, candidates, top_k=3)
        
        # After reranking, chunk 3 should be first (most relevant)
        assert reranked[0]['chunk_id'] == 3
        assert reranked[0]['rerank_score'] == 0.95
        assert reranked[0]['rerank_rank'] == 1

