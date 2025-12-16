"""
Reciprocal Rank Fusion (RRF) Service

Implements RRF algorithm to fuse results from multiple search methods
(semantic and keyword search) for improved retrieval precision.
"""
import logging
from typing import List, Dict, Optional, Any
from collections import defaultdict

from app.config.rrf_config import rrf_config

logger = logging.getLogger(__name__)


class RRFService:
    """
    Reciprocal Rank Fusion service for combining search results
    
    RRF Formula: score = α/(k + semantic_rank) + (1-α)/(k + keyword_rank)
    
    Where:
    - α (alpha): Weight for semantic search (0-1, default: 0.7)
    - k: RRF constant (default: 60)
    - semantic_rank: Rank position in semantic results (1-indexed)
    - keyword_rank: Rank position in keyword results (1-indexed)
    """
    
    def __init__(self, alpha: Optional[float] = None, k: Optional[int] = None):
        """
        Initialize RRF service
        
        Args:
            alpha: Weight for semantic search (0-1). If None, uses config default.
            k: RRF constant. If None, uses config default.
        """
        self.alpha = rrf_config.validate_alpha(alpha) if alpha is not None else rrf_config.ALPHA
        self.k = rrf_config.validate_k(k) if k is not None else rrf_config.K
        
        logger.debug(f"RRFService initialized with alpha={self.alpha}, k={self.k}")
    
    def fuse_results(
        self,
        semantic_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Fuse semantic and keyword search results using RRF
        
        Args:
            semantic_results: List of semantic search results with 'chunk_id' and 'similarity'
            keyword_results: List of keyword search results with 'chunk_id' and 'score'
            top_k: Number of top results to return
        
        Returns:
            Fused list of results sorted by RRF score (descending)
        """
        if not semantic_results and not keyword_results:
            logger.warning("Both result sets are empty")
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
            logger.warning("No valid chunk IDs found in results")
            return []
        
        # Calculate RRF scores for each chunk
        fused_results = []
        
        for chunk_id in all_chunk_ids:
            # Get ranks (use max rank + 1 if not present in a result set)
            semantic_rank = semantic_ranks.get(chunk_id)
            keyword_rank = keyword_ranks.get(chunk_id)
            
            # Calculate RRF score
            semantic_score = 0.0
            keyword_score = 0.0
            
            if semantic_rank is not None:
                semantic_score = self.alpha / (self.k + semantic_rank)
            
            if keyword_rank is not None:
                keyword_score = (1.0 - self.alpha) / (self.k + keyword_rank)
            
            rrf_score = semantic_score + keyword_score
            
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
                'rrf_score': rrf_score,
                'semantic_rank': semantic_rank,
                'keyword_rank': keyword_rank,
                'similarity': rrf_score,  # Use RRF score as main similarity for compatibility
                'retrieval_method': 'rrf_fusion'
            }
            
            # Preserve original scores if they exist
            if 'semantic_score' not in fused_result:
                fused_result['semantic_score'] = result_data.get('similarity', result_data.get('score', 0))
            if 'keyword_score' not in fused_result:
                fused_result['keyword_score'] = result_data.get('score', result_data.get('similarity', 0))
            
            fused_results.append(fused_result)
        
        # Sort by RRF score (descending)
        fused_results.sort(key=lambda x: x['rrf_score'], reverse=True)
        
        # Return top-k
        result = fused_results[:top_k]
        
        logger.debug(f"Fused {len(semantic_results)} semantic and {len(keyword_results)} keyword results into {len(result)} top results")
        
        return result
    
    def calculate_rrf_score(
        self,
        semantic_rank: Optional[int],
        keyword_rank: Optional[int]
    ) -> float:
        """
        Calculate RRF score for a single chunk
        
        Args:
            semantic_rank: Rank in semantic results (1-indexed, None if not present)
            keyword_rank: Rank in keyword results (1-indexed, None if not present)
        
        Returns:
            RRF score
        """
        semantic_score = 0.0
        keyword_score = 0.0
        
        if semantic_rank is not None:
            semantic_score = self.alpha / (self.k + semantic_rank)
        
        if keyword_rank is not None:
            keyword_score = (1.0 - self.alpha) / (self.k + keyword_rank)
        
        return semantic_score + keyword_score
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get current RRF configuration
        
        Returns:
            Dict with alpha, k, and weight information
        """
        return {
            'alpha': self.alpha,
            'k': self.k,
            'semantic_weight': self.alpha,
            'keyword_weight': 1.0 - self.alpha
        }

