"""
Reranker Service for Cross-Encoder Reranking

Improves retrieval precision by reranking initial search results
using cross-encoder models (Cohere API or sentence-transformers).
"""
import logging
import time
from typing import List, Dict, Optional, Any, Tuple

from app.config.reranker_config import reranker_config

logger = logging.getLogger(__name__)

# Try to import Cohere
try:
    import cohere
    COHERE_AVAILABLE = True
except ImportError:
    COHERE_AVAILABLE = False
    logger.warning("Cohere library not available. Install with: pip install cohere")

# Try to import sentence-transformers for fallback
try:
    from sentence_transformers import CrossEncoder
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available. Fallback reranking will be disabled.")


class RerankerService:
    """
    Cross-encoder reranker service for improving retrieval precision
    
    Uses Cohere Rerank API as primary method, falls back to
    sentence-transformers cross-encoder if Cohere is unavailable.
    """
    
    def __init__(self):
        """
        Initialize reranker service
        
        Attempts to initialize Cohere client, falls back to sentence-transformers if unavailable.
        """
        self.cohere_client = None
        self.fallback_model = None
        self.use_cohere = False
        self.use_fallback = False
        
        # Try to initialize Cohere
        if COHERE_AVAILABLE and reranker_config.is_cohere_available():
            try:
                self.cohere_client = cohere.Client(api_key=reranker_config.COHERE_API_KEY)
                self.use_cohere = True
                logger.info(f"RerankerService initialized with Cohere API (model: {reranker_config.COHERE_MODEL})")
            except Exception as e:
                logger.warning(f"Failed to initialize Cohere client: {e}. Will use fallback.")
                self.cohere_client = None
        
        # Initialize fallback model if Cohere not available
        if not self.use_cohere and SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.fallback_model = CrossEncoder(
                    reranker_config.FALLBACK_MODEL,
                    device=reranker_config.FALLBACK_DEVICE
                )
                self.use_fallback = True
                logger.info(f"RerankerService initialized with fallback model: {reranker_config.FALLBACK_MODEL}")
            except Exception as e:
                logger.warning(f"Failed to initialize fallback reranker: {e}")
                self.fallback_model = None
        
        if not self.use_cohere and not self.use_fallback:
            logger.warning("RerankerService initialized but no reranking method available. Reranking will be disabled.")
    
    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank candidates using cross-encoder
        
        Args:
            query: Search query text
            candidates: List of candidate results with 'chunk_text' and 'chunk_id'
            top_k: Number of top results to return (default: config.RERANK_TOP_K)
        
        Returns:
            Reranked list of results sorted by relevance score (descending)
        """
        if not reranker_config.RERANK_ENABLED:
            logger.debug("Reranking is disabled. Returning original results.")
            return candidates[:top_k or reranker_config.RERANK_TOP_K]
        
        if not candidates:
            logger.warning("No candidates provided for reranking")
            return []
        
        if top_k is None:
            top_k = reranker_config.RERANK_TOP_K
        
        start_time = time.time()
        
        try:
            # Limit candidates to top N for reranking
            candidates_to_rerank = candidates[:reranker_config.RERANK_TOP_N]
            
            # Try Cohere first
            if self.use_cohere and self.cohere_client:
                try:
                    reranked = self._rerank_with_cohere(query, candidates_to_rerank, top_k)
                    latency_ms = (time.time() - start_time) * 1000
                    logger.info(f"Reranked {len(candidates_to_rerank)} candidates using Cohere in {latency_ms:.2f}ms")
                    return reranked
                except Exception as e:
                    logger.warning(f"Cohere reranking failed: {e}. Falling back to sentence-transformers.")
                    if not reranker_config.FALLBACK_ON_ERROR:
                        if reranker_config.RETURN_ORIGINAL_ON_FAILURE:
                            return candidates[:top_k]
                        raise
            
            # Fallback to sentence-transformers
            if self.use_fallback and self.fallback_model:
                try:
                    reranked = self._rerank_with_fallback(query, candidates_to_rerank, top_k)
                    latency_ms = (time.time() - start_time) * 1000
                    logger.info(f"Reranked {len(candidates_to_rerank)} candidates using fallback model in {latency_ms:.2f}ms")
                    return reranked
                except Exception as e:
                    logger.error(f"Fallback reranking failed: {e}", exc_info=True)
                    if reranker_config.RETURN_ORIGINAL_ON_FAILURE:
                        logger.warning("Returning original results due to reranking failure")
                        return candidates[:top_k]
                    raise
            
            # No reranking available, return original
            logger.warning("No reranking method available. Returning original results.")
            return candidates[:top_k]
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}", exc_info=True)
            if reranker_config.RETURN_ORIGINAL_ON_FAILURE:
                return candidates[:top_k]
            raise
    
    def _rerank_with_cohere(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Rerank using Cohere Rerank API
        
        Args:
            query: Search query
            candidates: List of candidate results
            top_k: Number of top results to return
        
        Returns:
            Reranked results
        """
        # Prepare documents for Cohere API
        documents = [candidate.get('chunk_text', '') for candidate in candidates]
        
        # Call Cohere Rerank API
        response = self.cohere_client.rerank(
            model=reranker_config.COHERE_MODEL,
            query=query,
            documents=documents,
            top_n=top_k,
            return_documents=False  # We'll use original candidate data
        )
        
        # Map reranked results back to original candidates
        reranked_results = []
        for result in response.results:
            original_index = result.index
            if original_index < len(candidates):
                candidate = candidates[original_index].copy()
                candidate['rerank_score'] = result.relevance_score
                candidate['rerank_rank'] = len(reranked_results) + 1
                candidate['similarity'] = result.relevance_score  # Update similarity with rerank score
                candidate['rerank_method'] = 'cohere'
                reranked_results.append(candidate)
        
        return reranked_results
    
    def _rerank_with_fallback(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Rerank using sentence-transformers cross-encoder
        
        Args:
            query: Search query
            candidates: List of candidate results
            top_k: Number of top results to return
        
        Returns:
            Reranked results
        """
        # Prepare query-document pairs
        pairs = [
            [query, candidate.get('chunk_text', '')]
            for candidate in candidates
        ]
        
        # Get scores from cross-encoder
        scores = self.fallback_model.predict(
            pairs,
            batch_size=reranker_config.FALLBACK_BATCH_SIZE,
            show_progress_bar=False
        )
        
        # Create list of (score, index, candidate) tuples
        scored_candidates = [
            (float(score), idx, candidate)
            for idx, (score, candidate) in enumerate(zip(scores, candidates))
        ]
        
        # Sort by score (descending)
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        
        # Build reranked results
        reranked_results = []
        for rank, (score, original_idx, candidate) in enumerate(scored_candidates[:top_k], start=1):
            reranked_candidate = candidate.copy()
            reranked_candidate['rerank_score'] = float(score)
            reranked_candidate['rerank_rank'] = rank
            reranked_candidate['similarity'] = float(score)  # Update similarity with rerank score
            reranked_candidate['rerank_method'] = 'sentence-transformers'
            reranked_results.append(reranked_candidate)
        
        return reranked_results
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get reranker service status
        
        Returns:
            Dict with service status and configuration
        """
        return {
            'cohere_available': self.use_cohere and self.cohere_client is not None,
            'fallback_available': self.use_fallback and self.fallback_model is not None,
            'reranking_enabled': reranker_config.RERANK_ENABLED,
            'cohere_model': reranker_config.COHERE_MODEL if self.use_cohere else None,
            'fallback_model': reranker_config.FALLBACK_MODEL if self.use_fallback else None,
            'config': reranker_config.get_config_dict()
        }

