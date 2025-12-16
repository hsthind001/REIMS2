"""
Unit Tests for Fusion Service

Tests RRF fusion algorithm, parameter tuning, edge cases,
and integration scenarios.
"""
import pytest
from app.services.fusion_service import FusionService
from app.services.fusion_evaluation import FusionEvaluation
from app.config.fusion_config import fusion_config


class TestRRFFusion:
    """Test RRF fusion algorithm"""
    
    def test_fusion_basic(self):
        """Test basic fusion of two result lists"""
        service = FusionService(alpha=0.7, k=60)
        
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
        
        fused = service.fuse(semantic_results, keyword_results, top_k=5)
        
        assert len(fused) == 4  # All unique chunks
        assert all('fused_score' in r for r in fused)
        assert all('chunk_id' in r for r in fused)
        assert all('semantic_rank' in r for r in fused)
        assert all('keyword_rank' in r for r in fused)
        
        # Results should be sorted by fused score (descending)
        scores = [r['fused_score'] for r in fused]
        assert scores == sorted(scores, reverse=True)
    
    def test_fusion_formula_verification(self):
        """Test that fusion formula is correct"""
        service = FusionService(alpha=0.7, k=60)
        
        # Chunk at rank 1 in both
        fused_score, semantic_comp, keyword_comp = service.calculate_fused_score(
            semantic_rank=1, keyword_rank=1
        )
        
        expected_semantic = 0.7 * (1.0 / (60 + 1))
        expected_keyword = 0.3 * (1.0 / (60 + 1))
        expected_fused = expected_semantic + expected_keyword
        
        assert abs(semantic_comp - expected_semantic) < 0.0001
        assert abs(keyword_comp - expected_keyword) < 0.0001
        assert abs(fused_score - expected_fused) < 0.0001
    
    def test_fusion_only_semantic(self):
        """Test fusion when chunk only in semantic results"""
        service = FusionService(alpha=0.7, k=60)
        
        semantic_results = [
            {'chunk_id': 1, 'similarity': 0.9},
            {'chunk_id': 2, 'similarity': 0.8},
        ]
        
        keyword_results = []
        
        fused = service.fuse(semantic_results, keyword_results, top_k=5)
        
        assert len(fused) == 2
        assert all(r['semantic_rank'] is not None for r in fused)
        assert all(r['keyword_rank'] is None for r in fused)
        assert all(r['keyword_component'] == 0.0 for r in fused)
    
    def test_fusion_only_keyword(self):
        """Test fusion when chunk only in keyword results"""
        service = FusionService(alpha=0.7, k=60)
        
        semantic_results = []
        
        keyword_results = [
            {'chunk_id': 1, 'score': 2.5},
            {'chunk_id': 2, 'score': 2.0},
        ]
        
        fused = service.fuse(semantic_results, keyword_results, top_k=5)
        
        assert len(fused) == 2
        assert all(r['semantic_rank'] is None for r in fused)
        assert all(r['keyword_rank'] is not None for r in fused)
        assert all(r['semantic_component'] == 0.0 for r in fused)
    
    def test_fusion_preserves_metadata(self):
        """Test that fusion preserves metadata from both sources"""
        service = FusionService(alpha=0.7, k=60)
        
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
        
        fused = service.fuse(semantic_results, keyword_results, top_k=5)
        
        assert len(fused) == 1
        result = fused[0]
        
        # Should preserve all metadata
        assert result['chunk_id'] == 1
        assert result['property_id'] == 1
        assert 'document_type' in result
        assert 'period_id' in result
        assert 'fused_score' in result
        assert 'semantic_component' in result
        assert 'keyword_component' in result
    
    def test_fusion_logging(self):
        """Test fusion with score logging enabled"""
        service = FusionService(alpha=0.7, k=60)
        
        semantic_results = [
            {'chunk_id': 1, 'similarity': 0.9}
        ]
        
        keyword_results = [
            {'chunk_id': 1, 'score': 2.5}
        ]
        
        # Should not raise error with logging enabled
        fused = service.fuse(semantic_results, keyword_results, top_k=5, log_scores=True)
        
        assert len(fused) == 1
        assert fused[0]['fused_score'] > 0


class TestParameterTuning:
    """Test parameter tuning functionality"""
    
    def test_tune_alpha(self):
        """Test alpha parameter tuning"""
        service = FusionService(alpha=0.7, k=60)
        
        semantic_results = [
            {'chunk_id': 1, 'similarity': 0.9},
            {'chunk_id': 2, 'similarity': 0.8},
        ]
        
        keyword_results = [
            {'chunk_id': 2, 'score': 2.5},
            {'chunk_id': 1, 'score': 2.0},
        ]
        
        ground_truth = [1]  # Chunk 1 is relevant
        
        tuning_result = service.tune_alpha(
            semantic_results=semantic_results,
            keyword_results=keyword_results,
            ground_truth=ground_truth,
            alpha_range=(0.0, 1.0),
            alpha_step=0.5
        )
        
        assert 'best_alpha' in tuning_result
        assert 'best_score' in tuning_result
        assert 'alpha_scores' in tuning_result
        assert isinstance(tuning_result['best_alpha'], (int, float))
        assert 0.0 <= tuning_result['best_alpha'] <= 1.0
    
    def test_tune_k(self):
        """Test k parameter tuning"""
        service = FusionService(alpha=0.7, k=60)
        
        semantic_results = [
            {'chunk_id': 1, 'similarity': 0.9},
            {'chunk_id': 2, 'similarity': 0.8},
        ]
        
        keyword_results = [
            {'chunk_id': 2, 'score': 2.5},
            {'chunk_id': 1, 'score': 2.0},
        ]
        
        ground_truth = [1]
        
        tuning_result = service.tune_k(
            semantic_results=semantic_results,
            keyword_results=keyword_results,
            ground_truth=ground_truth,
            k_range=(30, 60),
            k_step=30
        )
        
        assert 'best_k' in tuning_result
        assert 'best_score' in tuning_result
        assert 'k_scores' in tuning_result
        assert isinstance(tuning_result['best_k'], int)
        assert tuning_result['best_k'] >= 30


class TestFusionEvaluation:
    """Test fusion evaluation metrics"""
    
    def test_precision_at_k(self):
        """Test precision@k calculation"""
        evaluator = FusionEvaluation(top_k=5)
        
        retrieved = [1, 2, 3, 4, 5]
        ground_truth = {1, 3, 5, 7, 9}
        
        precision = evaluator.precision_at_k(retrieved, ground_truth, k=5)
        
        # 3 out of 5 retrieved are relevant
        assert abs(precision - 0.6) < 0.0001
    
    def test_recall_at_k(self):
        """Test recall@k calculation"""
        evaluator = FusionEvaluation(top_k=5)
        
        retrieved = [1, 2, 3, 4, 5]
        ground_truth = [1, 3, 5, 7, 9]
        
        recall = evaluator.recall_at_k(retrieved, ground_truth, k=5)
        
        # 3 out of 5 relevant items retrieved
        assert abs(recall - 0.6) < 0.0001
    
    def test_f1_at_k(self):
        """Test F1@k calculation"""
        evaluator = FusionEvaluation(top_k=5)
        
        precision = 0.6
        recall = 0.6
        f1 = evaluator.f1_at_k(precision, recall)
        
        expected_f1 = 2 * (precision * recall) / (precision + recall)
        assert abs(f1 - expected_f1) < 0.0001
    
    def test_ndcg(self):
        """Test NDCG calculation"""
        evaluator = FusionEvaluation(top_k=5)
        
        results = [
            {'chunk_id': 1},  # Relevant
            {'chunk_id': 2},  # Not relevant
            {'chunk_id': 3},  # Relevant
            {'chunk_id': 4},  # Not relevant
            {'chunk_id': 5},  # Relevant
        ]
        
        ground_truth = {1, 3, 5, 7, 9}
        
        ndcg = evaluator.ndcg(results, ground_truth, k=5)
        
        # Should be between 0 and 1
        assert 0.0 <= ndcg <= 1.0
    
    def test_mrr(self):
        """Test MRR calculation"""
        evaluator = FusionEvaluation()
        
        results = [
            {'chunk_id': 1},  # Not relevant
            {'chunk_id': 2},  # Not relevant
            {'chunk_id': 3},  # Relevant (rank 3)
        ]
        
        ground_truth = {3, 5}
        
        mrr = evaluator.mrr(results, ground_truth)
        
        # First relevant at rank 3, so MRR = 1/3
        assert abs(mrr - (1.0 / 3)) < 0.0001
    
    def test_evaluate(self):
        """Test full evaluation"""
        evaluator = FusionEvaluation(top_k=5)
        
        fused_results = [
            {'chunk_id': 1, 'fused_score': 0.9},
            {'chunk_id': 2, 'fused_score': 0.8},
            {'chunk_id': 3, 'fused_score': 0.7},
        ]
        
        ground_truth = [1, 3, 5]
        
        metrics = evaluator.evaluate(fused_results, ground_truth)
        
        assert 'precision_at_k' in metrics
        assert 'recall_at_k' in metrics
        assert 'f1_at_k' in metrics
        assert 'ndcg' in metrics
        assert 'mrr' in metrics
        assert all(0.0 <= v <= 1.0 for k, v in metrics.items() if isinstance(v, float))


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_fusion_empty_results(self):
        """Test fusion with empty result sets"""
        service = FusionService(alpha=0.7, k=60)
        
        fused = service.fuse([], [], top_k=5)
        
        assert fused == []
    
    def test_fusion_missing_chunk_id(self):
        """Test handling of results without chunk_id"""
        service = FusionService(alpha=0.7, k=60)
        
        semantic_results = [
            {'similarity': 0.9},  # Missing chunk_id
            {'chunk_id': 1, 'similarity': 0.8},
        ]
        
        keyword_results = [
            {'chunk_id': 1, 'score': 2.0},
        ]
        
        fused = service.fuse(semantic_results, keyword_results, top_k=5)
        
        # Should only include results with valid chunk_id
        assert len(fused) == 1
        assert fused[0]['chunk_id'] == 1
    
    def test_fusion_different_alpha_values(self):
        """Test fusion with different alpha values"""
        # Alpha = 0.9 (heavily weighted toward semantic)
        service_high_alpha = FusionService(alpha=0.9, k=60)
        
        semantic_results = [
            {'chunk_id': 1, 'similarity': 0.9},
            {'chunk_id': 2, 'similarity': 0.8},
        ]
        
        keyword_results = [
            {'chunk_id': 2, 'score': 2.5},
            {'chunk_id': 1, 'score': 2.0},
        ]
        
        fused_high = service_high_alpha.fuse(semantic_results, keyword_results, top_k=5)
        
        # Alpha = 0.1 (heavily weighted toward keyword)
        service_low_alpha = FusionService(alpha=0.1, k=60)
        fused_low = service_low_alpha.fuse(semantic_results, keyword_results, top_k=5)
        
        # With high alpha, semantic rank 1 should rank higher
        # With low alpha, keyword rank 1 should rank higher
        assert fused_high[0]['chunk_id'] == 1  # Semantic rank 1
        assert fused_low[0]['chunk_id'] == 2  # Keyword rank 1
    
    def test_calculate_fused_score_components(self):
        """Test that calculate_fused_score returns all components"""
        service = FusionService(alpha=0.7, k=60)
        
        fused_score, semantic_comp, keyword_comp = service.calculate_fused_score(
            semantic_rank=1, keyword_rank=1
        )
        
        assert fused_score > 0
        assert semantic_comp > 0
        assert keyword_comp > 0
        assert abs(fused_score - (semantic_comp + keyword_comp)) < 0.0001


class TestConfiguration:
    """Test configuration and parameter handling"""
    
    def test_default_parameters(self):
        """Test that default parameters are used"""
        service = FusionService()
        
        assert service.alpha == fusion_config.ALPHA
        assert service.k == fusion_config.K
    
    def test_custom_parameters(self):
        """Test custom parameters"""
        service = FusionService(alpha=0.5, k=30)
        
        assert service.alpha == 0.5
        assert service.k == 30
    
    def test_get_config(self):
        """Test getting configuration"""
        service = FusionService(alpha=0.7, k=60)
        
        config = service.get_config()
        
        assert config['alpha'] == 0.7
        assert config['k'] == 60
        assert config['semantic_weight'] == 0.7
        assert config['keyword_weight'] == 0.3
        assert 'formula' in config

