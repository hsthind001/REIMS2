"""
Fusion Service for Combining Search Results

Implements Reciprocal Rank Fusion (RRF) to combine results from
semantic and keyword search methods for improved retrieval precision.

Formula: fused_score = α * (1 / (k + semantic_rank)) + (1 - α) * (1 / (k + keyword_rank))
"""
import logging
from typing import List, Dict, Optional, Any, Tuple
from collections import defaultdict

from app.config.rrf_config import rrf_config

logger = logging.getLogger(__name__)


class FusionService:
    """
    Fusion service for combining search results using RRF
    
    RRF Formula: fused_score = α * (1 / (k + semantic_rank)) + (1 - α) * (1 / (k + keyword_rank))
    
    Where:
    - α (alpha): Weight for semantic search (0-1, default: 0.7)
    - k: RRF constant (default: 60)
    - semantic_rank: Rank position in semantic results (1-indexed)
    - keyword_rank: Rank position in keyword results (1-indexed)
    """
    
    def __init__(self, alpha: Optional[float] = None, k: Optional[int] = None):
        """
        Initialize fusion service
        
        Args:
            alpha: Weight for semantic search (0-1). If None, uses config default.
            k: RRF constant. If None, uses config default.
        """
        self.alpha = rrf_config.validate_alpha(alpha) if alpha is not None else rrf_config.ALPHA
        self.k = rrf_config.validate_k(k) if k is not None else rrf_config.K
        
        logger.info(f"FusionService initialized with alpha={self.alpha}, k={self.k}")
    
    def fuse(
        self,
        semantic_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        top_k: int = 20,
        log_scores: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Fuse semantic and keyword search results using RRF
        
        Args:
            semantic_results: List of semantic search results with 'chunk_id' and 'similarity'
            keyword_results: List of keyword search results with 'chunk_id' and 'score'
            top_k: Number of top results to return
            log_scores: If True, log fusion scores for debugging
        
        Returns:
            Fused list of results sorted by RRF score (descending)
        """
        if not semantic_results and not keyword_results:
            logger.warning("Both result sets are empty for fusion")
            return []
        
        # Build rank maps: chunk_id -> rank (1-indexed)
        semantic_ranks = {}
        keyword_ranks = {}
        
        for rank, result in enumerate(semantic_results, start=1):
            chunk_id = result.get('chunk_id')
            if chunk_id is not None:
                semantic_ranks[chunk_id] = rank
        
        for rank, result in enumerate(keyword_results, start=1):
            chunk_id = result.get('chunk_id')
            if chunk_id is not None:
                keyword_ranks[chunk_id] = rank
        
        # Combine all unique chunk IDs
        all_chunk_ids = set(semantic_ranks.keys()) | set(keyword_ranks.keys())
        
        if not all_chunk_ids:
            logger.warning("No valid chunk IDs found in results for fusion")
            return []
        
        # Calculate RRF scores for each chunk
        fused_results = []
        
        for chunk_id in all_chunk_ids:
            # Get ranks (None if not present in a result set)
            semantic_rank = semantic_ranks.get(chunk_id)
            keyword_rank = keyword_ranks.get(chunk_id)
            
            # Calculate RRF score using the formula
            # fused_score = α * (1 / (k + semantic_rank)) + (1 - α) * (1 / (k + keyword_rank))
            semantic_component = 0.0
            keyword_component = 0.0
            
            if semantic_rank is not None:
                semantic_component = self.alpha * (1.0 / (self.k + semantic_rank))
            
            if keyword_rank is not None:
                keyword_component = (1.0 - self.alpha) * (1.0 / (self.k + keyword_rank))
            
            fused_score = semantic_component + keyword_component
            
            # Log fusion scores if requested
            if log_scores:
                logger.debug(
                    f"Fusion score for chunk {chunk_id}: "
                    f"fused={fused_score:.6f} "
                    f"(semantic_rank={semantic_rank}, keyword_rank={keyword_rank}, "
                    f"semantic_component={semantic_component:.6f}, keyword_component={keyword_component:.6f})"
                )
            
            # Get the result data (prefer semantic if both exist, otherwise use whichever is available)
            if chunk_id in semantic_ranks:
                result_data = next(
                    (r for r in semantic_results if r.get('chunk_id') == chunk_id),
                    {}
                )
            else:
                result_data = next(
                    (r for r in keyword_results if r.get('chunk_id') == chunk_id),
                    {}
                )
            
            # Merge data from both sources if available
            if chunk_id in semantic_ranks and chunk_id in keyword_ranks:
                semantic_data = next(
                    (r for r in semantic_results if r.get('chunk_id') == chunk_id),
                    {}
                )
                keyword_data = next(
                    (r for r in keyword_results if r.get('chunk_id') == chunk_id),
                    {}
                )
                # Merge, preferring semantic for most fields, but preserving both scores
                result_data = {**keyword_data, **semantic_data}  # Semantic overwrites keyword
                result_data['semantic_score'] = semantic_data.get('similarity', semantic_data.get('score', 0))
                result_data['keyword_score'] = keyword_data.get('score', keyword_data.get('similarity', 0))
            
            # Create fused result
            fused_result = {
                **result_data,  # Preserve all original metadata
                'chunk_id': chunk_id,
                'fused_score': fused_score,
                'semantic_rank': semantic_rank,
                'keyword_rank': keyword_rank,
                'semantic_component': semantic_component,
                'keyword_component': keyword_component,
                'similarity': fused_score,  # Use fused score as main similarity for compatibility
                'retrieval_method': 'rrf_fusion'
            }
            
            # Preserve original scores if they exist
            if 'semantic_score' not in fused_result:
                fused_result['semantic_score'] = result_data.get('similarity', result_data.get('score', 0))
            if 'keyword_score' not in fused_result:
                fused_result['keyword_score'] = result_data.get('score', result_data.get('similarity', 0))
            
            fused_results.append(fused_result)
        
        # Sort by fused score (descending)
        fused_results.sort(key=lambda x: x['fused_score'], reverse=True)
        
        # Return top-k
        result = fused_results[:top_k]
        
        logger.info(
            f"Fused {len(semantic_results)} semantic and {len(keyword_results)} keyword results "
            f"into {len(result)} top results (alpha={self.alpha}, k={self.k})"
        )
        
        return result
    
    def calculate_fused_score(
        self,
        semantic_rank: Optional[int],
        keyword_rank: Optional[int]
    ) -> Tuple[float, float, float]:
        """
        Calculate fused score for a single chunk
        
        Args:
            semantic_rank: Rank in semantic results (1-indexed, None if not present)
            keyword_rank: Rank in keyword results (1-indexed, None if not present)
        
        Returns:
            Tuple of (fused_score, semantic_component, keyword_component)
        """
        semantic_component = 0.0
        keyword_component = 0.0
        
        if semantic_rank is not None:
            semantic_component = self.alpha * (1.0 / (self.k + semantic_rank))
        
        if keyword_rank is not None:
            keyword_component = (1.0 - self.alpha) * (1.0 / (self.k + keyword_rank))
        
        fused_score = semantic_component + keyword_component
        
        return fused_score, semantic_component, keyword_component
    
    def tune_alpha(
        self,
        semantic_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        ground_truth: List[int],
        alpha_range: Tuple[float, float] = (0.0, 1.0),
        alpha_step: float = 0.1
    ) -> Dict[str, Any]:
        """
        Tune alpha parameter to find optimal value
        
        Args:
            semantic_results: Semantic search results
            keyword_results: Keyword search results
            ground_truth: List of chunk_ids that are relevant (ground truth)
            alpha_range: Range of alpha values to test (min, max)
            alpha_step: Step size for alpha values
        
        Returns:
            Dict with best alpha, scores for each alpha, and metrics
        """
        from app.services.fusion_evaluation import FusionEvaluation
        
        best_alpha = None
        best_score = 0.0
        alpha_scores = []
        
        alpha_min, alpha_max = alpha_range
        current_alpha = alpha_min
        
        while current_alpha <= alpha_max:
            # Create temporary fusion service with this alpha
            temp_service = FusionService(alpha=current_alpha, k=self.k)
            
            # Fuse results
            fused = temp_service.fuse(
                semantic_results=semantic_results,
                keyword_results=keyword_results,
                top_k=len(ground_truth) * 2  # Get enough results for evaluation
            )
            
            # Evaluate
            evaluator = FusionEvaluation()
            metrics = evaluator.evaluate(fused, ground_truth)
            
            # Use precision@k as the score (can be customized)
            score = metrics.get('precision_at_k', 0.0)
            
            alpha_scores.append({
                'alpha': current_alpha,
                'score': score,
                'metrics': metrics
            })
            
            if score > best_score:
                best_score = score
                best_alpha = current_alpha
            
            current_alpha += alpha_step
            current_alpha = round(current_alpha, 2)  # Round to avoid floating point issues
        
        return {
            'best_alpha': best_alpha,
            'best_score': best_score,
            'alpha_scores': alpha_scores,
            'k': self.k
        }
    
    def tune_k(
        self,
        semantic_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        ground_truth: List[int],
        k_range: Tuple[int, int] = (30, 100),
        k_step: int = 10
    ) -> Dict[str, Any]:
        """
        Tune k parameter to find optimal value
        
        Args:
            semantic_results: Semantic search results
            keyword_results: Keyword search results
            ground_truth: List of chunk_ids that are relevant (ground truth)
            k_range: Range of k values to test (min, max)
            k_step: Step size for k values
        
        Returns:
            Dict with best k, scores for each k, and metrics
        """
        from app.services.fusion_evaluation import FusionEvaluation
        
        best_k = None
        best_score = 0.0
        k_scores = []
        
        k_min, k_max = k_range
        current_k = k_min
        
        while current_k <= k_max:
            # Create temporary fusion service with this k
            temp_service = FusionService(alpha=self.alpha, k=current_k)
            
            # Fuse results
            fused = temp_service.fuse(
                semantic_results=semantic_results,
                keyword_results=keyword_results,
                top_k=len(ground_truth) * 2
            )
            
            # Evaluate
            evaluator = FusionEvaluation()
            metrics = evaluator.evaluate(fused, ground_truth)
            
            # Use precision@k as the score
            score = metrics.get('precision_at_k', 0.0)
            
            k_scores.append({
                'k': current_k,
                'score': score,
                'metrics': metrics
            })
            
            if score > best_score:
                best_score = score
                best_k = current_k
            
            current_k += k_step
        
        return {
            'best_k': best_k,
            'best_score': best_score,
            'k_scores': k_scores,
            'alpha': self.alpha
        }
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get current fusion configuration
        
        Returns:
            Dict with alpha, k, and weight information
        """
        return {
            'alpha': self.alpha,
            'k': self.k,
            'semantic_weight': self.alpha,
            'keyword_weight': 1.0 - self.alpha,
            'formula': f'fused_score = {self.alpha} * (1 / ({self.k} + semantic_rank)) + {1 - self.alpha} * (1 / ({self.k} + keyword_rank))'
        }

