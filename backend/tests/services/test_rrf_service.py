"""
Unit Tests for Reciprocal Rank Fusion (RRF) Service

Tests RRF fusion algorithm, parameter validation, edge cases,
and integration scenarios.
"""
import pytest
from app.services.rrf_service import RRFService
from app.config.rrf_config import rrf_config


class TestRRFScoreCalculation:
    """Test RRF score calculation"""
    
    def test_rrf_score_both_ranks(self):
        """Test RRF score when chunk appears in both result sets"""
        service = RRFService(alpha=0.7, k=60)
        
        # Chunk at rank 1 in both
        score = service.calculate_rrf_score(semantic_rank=1, keyword_rank=1)
        expected = (0.7 / (60 + 1)) + (0.3 / (60 + 1))
        assert abs(score - expected) < 0.0001
        
        # Chunk at different ranks
        score = service.calculate_rrf_score(semantic_rank=1, keyword_rank=5)
        expected = (0.7 / (60 + 1)) + (0.3 / (60 + 5))
        assert abs(score - expected) < 0.0001
    
    def test_rrf_score_only_semantic(self):
        """Test RRF score when chunk only in semantic results"""
        service = RRFService(alpha=0.7, k=60)
        
        score = service.calculate_rrf_score(semantic_rank=1, keyword_rank=None)
        expected = 0.7 / (60 + 1)
        assert abs(score - expected) < 0.0001
    
    def test_rrf_score_only_keyword(self):
        """Test RRF score when chunk only in keyword results"""
        service = RRFService(alpha=0.7, k=60)
        
        score = service.calculate_rrf_score(semantic_rank=None, keyword_rank=1)
        expected = 0.3 / (60 + 1)
        assert abs(score - expected) < 0.0001
    
    def test_rrf_score_alpha_0(self):
        """Test RRF with alpha=0 (only keyword matters)"""
        service = RRFService(alpha=0.0, k=60)
        
        score = service.calculate_rrf_score(semantic_rank=1, keyword_rank=1)
        expected = (0.0 / (60 + 1)) + (1.0 / (60 + 1))
        assert abs(score - expected) < 0.0001
    
    def test_rrf_score_alpha_1(self):
        """Test RRF with alpha=1 (only semantic matters)"""
        service = RRFService(alpha=1.0, k=60)
        
        score = service.calculate_rrf_score(semantic_rank=1, keyword_rank=1)
        expected = (1.0 / (60 + 1)) + (0.0 / (60 + 1))
        assert abs(score - expected) < 0.0001
    
    def test_rrf_score_different_k(self):
        """Test RRF with different k values"""
        service = RRFService(alpha=0.7, k=10)
        
        score = service.calculate_rrf_score(semantic_rank=1, keyword_rank=1)
        expected = (0.7 / (10 + 1)) + (0.3 / (10 + 1))
        assert abs(score - expected) < 0.0001


class TestRRFFusion:
    """Test RRF fusion of result lists"""
    
    def test_fuse_results_basic(self):
        """Test basic fusion of two result lists"""
        service = RRFService(alpha=0.7, k=60)
        
        semantic_results = [
            {'chunk_id': 1, 'similarity': 0.9, 'chunk_text': 'Text 1'},
            {'chunk_id': 2, 'similarity': 0.8, 'chunk_text': 'Text 2'},
            {'chunk_id': 3, 'similarity': 0.7, 'chunk_text': 'Text 3'},
        ]
        
        keyword_results = [
            {'chunk_id': 2, 'score': 2.5, 'chunk_text': 'Text 2'},
            {'chunk_id': 1, 'score': 2.0, 'chunk_text': 'Text 1'},
            {'chunk_id': 4, 'score': 1.8, 'chunk_text': 'Text 4'},
        ]
        
        fused = service.fuse_results(semantic_results, keyword_results, top_k=5)
        
        assert len(fused) == 4  # All unique chunks
        assert all('rrf_score' in r for r in fused)
        assert all('chunk_id' in r for r in fused)
        
        # Results should be sorted by RRF score (descending)
        scores = [r['rrf_score'] for r in fused]
        assert scores == sorted(scores, reverse=True)
    
    def test_fuse_results_deduplication(self):
        """Test that duplicate chunk_ids are deduplicated"""
        service = RRFService(alpha=0.7, k=60)
        
        semantic_results = [
            {'chunk_id': 1, 'similarity': 0.9},
            {'chunk_id': 1, 'similarity': 0.8},  # Duplicate
        ]
        
        keyword_results = [
            {'chunk_id': 1, 'score': 2.0},
        ]
        
        fused = service.fuse_results(semantic_results, keyword_results, top_k=5)
        
        # Should only have one result for chunk_id=1
        chunk_ids = [r['chunk_id'] for r in fused]
        assert chunk_ids.count(1) == 1
        assert len(fused) == 1
    
    def test_fuse_results_top_k(self):
        """Test that fusion returns top-k results"""
        service = RRFService(alpha=0.7, k=60)
        
        semantic_results = [
            {'chunk_id': i, 'similarity': 0.9 - i * 0.1}
            for i in range(1, 11)
        ]
        
        keyword_results = [
            {'chunk_id': i, 'score': 2.0 - i * 0.1}
            for i in range(1, 11)
        ]
        
        fused = service.fuse_results(semantic_results, keyword_results, top_k=5)
        
        assert len(fused) == 5
        assert all(r['chunk_id'] <= 5 for r in fused)  # Top 5 should have highest scores
    
    def test_fuse_results_only_semantic(self):
        """Test fusion when only semantic results exist"""
        service = RRFService(alpha=0.7, k=60)
        
        semantic_results = [
            {'chunk_id': 1, 'similarity': 0.9},
            {'chunk_id': 2, 'similarity': 0.8},
        ]
        
        keyword_results = []
        
        fused = service.fuse_results(semantic_results, keyword_results, top_k=5)
        
        assert len(fused) == 2
        assert all('rrf_score' in r for r in fused)
        assert all(r['semantic_rank'] is not None for r in fused)
        assert all(r['keyword_rank'] is None for r in fused)
    
    def test_fuse_results_only_keyword(self):
        """Test fusion when only keyword results exist"""
        service = RRFService(alpha=0.7, k=60)
        
        semantic_results = []
        
        keyword_results = [
            {'chunk_id': 1, 'score': 2.5},
            {'chunk_id': 2, 'score': 2.0},
        ]
        
        fused = service.fuse_results(semantic_results, keyword_results, top_k=5)
        
        assert len(fused) == 2
        assert all('rrf_score' in r for r in fused)
        assert all(r['semantic_rank'] is None for r in fused)
        assert all(r['keyword_rank'] is not None for r in fused)
    
    def test_fuse_results_empty_both(self):
        """Test fusion when both result sets are empty"""
        service = RRFService(alpha=0.7, k=60)
        
        fused = service.fuse_results([], [], top_k=5)
        
        assert fused == []
    
    def test_fuse_results_preserves_metadata(self):
        """Test that fusion preserves metadata from both sources"""
        service = RRFService(alpha=0.7, k=60)
        
        semantic_results = [
            {
                'chunk_id': 1,
                'similarity': 0.9,
                'chunk_text': 'Semantic text',
                'property_id': 1,
                'document_type': 'income_statement'
            }
        ]
        
        keyword_results = [
            {
                'chunk_id': 1,
                'score': 2.5,
                'chunk_text': 'Keyword text',
                'property_id': 1,
                'period_id': 2023
            }
        ]
        
        fused = service.fuse_results(semantic_results, keyword_results, top_k=5)
        
        assert len(fused) == 1
        result = fused[0]
        
        # Should preserve all metadata
        assert result['chunk_id'] == 1
        assert result['property_id'] == 1
        assert 'document_type' in result
        assert 'period_id' in result
        assert 'rrf_score' in result
        assert 'semantic_rank' in result
        assert 'keyword_rank' in result
        assert 'semantic_score' in result
        assert 'keyword_score' in result
    
    def test_fuse_results_preserves_original_scores(self):
        """Test that original scores are preserved for debugging"""
        service = RRFService(alpha=0.7, k=60)
        
        semantic_results = [
            {'chunk_id': 1, 'similarity': 0.9}
        ]
        
        keyword_results = [
            {'chunk_id': 1, 'score': 2.5}
        ]
        
        fused = service.fuse_results(semantic_results, keyword_results, top_k=5)
        
        assert len(fused) == 1
        result = fused[0]
        
        # Should have both original scores
        assert 'semantic_score' in result
        assert 'keyword_score' in result
        assert result['semantic_score'] == 0.9
        assert result['keyword_score'] == 2.5


class TestRRFParameters:
    """Test RRF parameter handling"""
    
    def test_default_parameters(self):
        """Test that default parameters are used"""
        service = RRFService()
        
        assert service.alpha == rrf_config.ALPHA
        assert service.k == rrf_config.K
    
    def test_custom_alpha(self):
        """Test custom alpha parameter"""
        service = RRFService(alpha=0.5)
        
        assert service.alpha == 0.5
        assert service.k == rrf_config.K
    
    def test_custom_k(self):
        """Test custom k parameter"""
        service = RRFService(k=30)
        
        assert service.alpha == rrf_config.ALPHA
        assert service.k == 30
    
    def test_alpha_clamping(self):
        """Test that alpha is clamped to valid range"""
        service = RRFService(alpha=-0.5)  # Below minimum
        assert service.alpha == 0.0
        
        service = RRFService(alpha=1.5)  # Above maximum
        assert service.alpha == 1.0
    
    def test_k_clamping(self):
        """Test that k is clamped to valid range"""
        service = RRFService(k=0)  # Below minimum
        assert service.k == 1
        
        service = RRFService(k=2000)  # Above maximum
        assert service.k == 1000
    
    def test_get_config(self):
        """Test getting configuration"""
        service = RRFService(alpha=0.7, k=60)
        
        config = service.get_config()
        
        assert config['alpha'] == pytest.approx(0.7)
        assert config['k'] == 60
        assert config['semantic_weight'] == pytest.approx(0.7)
        assert config['keyword_weight'] == pytest.approx(0.3)


class TestRRFEdgeCases:
    """Test edge cases and error handling"""
    
    def test_fuse_results_missing_chunk_id(self):
        """Test handling of results without chunk_id"""
        service = RRFService(alpha=0.7, k=60)
        
        semantic_results = [
            {'similarity': 0.9},  # Missing chunk_id
            {'chunk_id': 1, 'similarity': 0.8},
        ]
        
        keyword_results = [
            {'chunk_id': 1, 'score': 2.0},
        ]
        
        fused = service.fuse_results(semantic_results, keyword_results, top_k=5)
        
        # Should only include results with valid chunk_id
        assert len(fused) == 1
        assert fused[0]['chunk_id'] == 1
    
    def test_fuse_results_different_alpha_values(self):
        """Test fusion with different alpha values"""
        # Alpha = 0.9 (heavily weighted toward semantic)
        service_high_alpha = RRFService(alpha=0.9, k=60)
        
        semantic_results = [
            {'chunk_id': 1, 'similarity': 0.9},
            {'chunk_id': 2, 'similarity': 0.8},
        ]
        
        keyword_results = [
            {'chunk_id': 2, 'score': 2.5},
            {'chunk_id': 1, 'score': 2.0},
        ]
        
        fused_high = service_high_alpha.fuse_results(semantic_results, keyword_results, top_k=5)
        
        # Alpha = 0.1 (heavily weighted toward keyword)
        service_low_alpha = RRFService(alpha=0.1, k=60)
        fused_low = service_low_alpha.fuse_results(semantic_results, keyword_results, top_k=5)
        
        # With high alpha, semantic rank 1 should rank higher
        # With low alpha, keyword rank 1 should rank higher
        assert fused_high[0]['chunk_id'] == 1  # Semantic rank 1
        assert fused_low[0]['chunk_id'] == 2  # Keyword rank 1
    
    def test_fuse_results_large_k(self):
        """Test fusion with large k value"""
        service = RRFService(alpha=0.7, k=1000)
        
        semantic_results = [
            {'chunk_id': 1, 'similarity': 0.9},
        ]
        
        keyword_results = [
            {'chunk_id': 1, 'score': 2.5},
        ]
        
        fused = service.fuse_results(semantic_results, keyword_results, top_k=5)
        
        # Should still work with large k
        assert len(fused) == 1
        assert fused[0]['rrf_score'] > 0
    
    def test_fuse_results_rank_ordering(self):
        """Test that lower ranks get higher RRF scores"""
        service = RRFService(alpha=0.5, k=60)
        
        semantic_results = [
            {'chunk_id': 1, 'similarity': 0.9},  # Rank 1
            {'chunk_id': 2, 'similarity': 0.8},  # Rank 2
            {'chunk_id': 3, 'similarity': 0.7},  # Rank 3
        ]
        
        keyword_results = [
            {'chunk_id': 1, 'score': 2.5},  # Rank 1
            {'chunk_id': 2, 'score': 2.0},  # Rank 2
            {'chunk_id': 3, 'score': 1.5},  # Rank 3
        ]
        
        fused = service.fuse_results(semantic_results, keyword_results, top_k=5)
        
        # All chunks appear in both, so rank 1 should have highest score
        assert fused[0]['chunk_id'] == 1
        assert fused[0]['rrf_score'] > fused[1]['rrf_score']
        assert fused[1]['rrf_score'] > fused[2]['rrf_score']

