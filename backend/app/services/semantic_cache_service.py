"""
Semantic Cache Service for NLQ

Provides embedding-based semantic caching for Natural Language Queries
to match paraphrased questions and achieve >30% cache hit rate.
"""
import logging
import time
import hashlib
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

import numpy as np

# Prometheus metrics
try:
    from prometheus_client import Counter, Gauge, Histogram
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("Prometheus client not available. Metrics will not be tracked.")

from app.models.nlq_query import NLQQuery
from app.services.embedding_service import EmbeddingService
from app.config.cache_config import cache_config

logger = logging.getLogger(__name__)

# Initialize Prometheus metrics
if PROMETHEUS_AVAILABLE:
    nlq_cache_hits_total = Counter(
        'nlq_cache_hits_total',
        'Total number of NLQ cache hits'
    )
    
    nlq_cache_misses_total = Counter(
        'nlq_cache_misses_total',
        'Total number of NLQ cache misses'
    )
    
    nlq_cache_hit_rate = Gauge(
        'nlq_cache_hit_rate',
        'Current NLQ cache hit rate (0-1)'
    )
    
    nlq_cache_lookup_time_seconds = Histogram(
        'nlq_cache_lookup_time_seconds',
        'Time taken for cache lookup',
        buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
    )
    
    nlq_cache_similarity_score = Histogram(
        'nlq_cache_similarity_score',
        'Similarity scores of cache hits',
        buckets=[0.85, 0.90, 0.92, 0.94, 0.95, 0.96, 0.98, 0.99, 1.0]
    )
else:
    # Dummy metrics if Prometheus not available
    class DummyMetric:
        def inc(self, *args, **kwargs): pass
        def set(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
    
    nlq_cache_hits_total = DummyMetric()
    nlq_cache_misses_total = DummyMetric()
    nlq_cache_hit_rate = DummyMetric()
    nlq_cache_lookup_time_seconds = DummyMetric()
    nlq_cache_similarity_score = DummyMetric()


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors using NumPy
    
    Args:
        vec1: First vector
        vec2: Second vector
    
    Returns:
        Similarity score between -1 and 1 (typically 0-1 for embeddings)
    """
    if not vec1 or not vec2:
        return 0.0
    
    if len(vec1) != len(vec2):
        logger.warning(f"Vector dimension mismatch: {len(vec1)} vs {len(vec2)}")
        return 0.0
    
    try:
        # Convert to numpy arrays
        v1 = np.array(vec1, dtype=np.float32)
        v2 = np.array(vec2, dtype=np.float32)
        
        # Calculate cosine similarity
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        
        # Ensure result is in valid range
        return float(np.clip(similarity, -1.0, 1.0))
    
    except Exception as e:
        logger.error(f"Error calculating cosine similarity: {e}", exc_info=True)
        return 0.0


class SemanticCacheService:
    """
    Semantic cache service for NLQ queries
    
    Features:
    - Embedding-based similarity matching
    - Quick hash-based exact match fallback
    - TTL-based cache expiration
    - Performance monitoring
    - Graceful degradation
    """
    
    def __init__(self, db: Session, embedding_service: Optional[EmbeddingService] = None):
        """
        Initialize semantic cache service
        
        Args:
            db: SQLAlchemy database session
            embedding_service: EmbeddingService instance (optional, will create if not provided)
        """
        self.db = db
        self.embedding_service = embedding_service or EmbeddingService(db)
        self._cache_stats = {
            'hits': 0,
            'misses': 0,
            'last_update': datetime.now()
        }
    
    def find_similar_query(
        self,
        question: str,
        user_id: Optional[int] = None,
        threshold: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find a similar cached query using semantic similarity
        
        Strategy:
        1. Quick hash check for exact match (fastest)
        2. Embedding search for semantic match
        3. Return best match if similarity >= threshold
        
        Args:
            question: User's question
            user_id: Optional user ID to filter by user
            threshold: Similarity threshold (defaults to config value)
        
        Returns:
            Dict with cached query data or None if no match found
        """
        if not cache_config.ENABLE_SEMANTIC_CACHE:
            return None
        
        start_time = time.time()
        threshold = threshold or cache_config.SIMILARITY_THRESHOLD
        
        try:
            # Step 1: Quick hash check for exact match
            question_hash = self._calculate_hash(question)
            exact_match = self._find_exact_match(question_hash, user_id)
            
            if exact_match:
                elapsed = (time.time() - start_time) * 1000  # Convert to ms
                self._record_cache_hit(exact_match, 1.0, elapsed)
                return exact_match.to_dict()
            
            # Step 2: Generate embedding for question
            embedding = self.embedding_service.generate_embedding(question)
            
            if not embedding:
                logger.warning("Could not generate embedding for cache lookup, falling back to exact match")
                nlq_cache_misses_total.inc()
                return None
            
            # Step 3: Search for similar queries
            similar_query = self._find_similar_by_embedding(
                embedding=embedding,
                question_hash=question_hash,
                user_id=user_id,
                threshold=threshold
            )
            
            elapsed = (time.time() - start_time) * 1000  # Convert to ms
            
            if similar_query:
                similarity = similar_query.get('similarity', 0.0)
                self._record_cache_hit(similar_query, similarity, elapsed)
                return similar_query
            
            # No match found
            nlq_cache_misses_total.inc()
            nlq_cache_lookup_time_seconds.observe(elapsed / 1000.0)
            self._update_cache_stats(miss=True)
            
            return None
            
        except Exception as e:
            logger.error(f"Error in cache lookup: {e}", exc_info=True)
            nlq_cache_misses_total.inc()
            return None
    
    def store_query_with_embedding(
        self,
        query_id: int,
        question: str,
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        Store query with embedding and hash
        
        Args:
            query_id: NLQQuery ID
            question: Question text
            force_regenerate: Force regeneration of embedding even if exists
        
        Returns:
            Dict with storage result
        """
        try:
            query = self.db.query(NLQQuery).filter(NLQQuery.id == query_id).first()
            
            if not query:
                return {"success": False, "error": f"Query {query_id} not found"}
            
            # Check if embedding already exists
            if query.question_embedding and not force_regenerate:
                return {"success": True, "message": "Embedding already exists"}
            
            # Generate embedding
            embedding = self.embedding_service.generate_embedding(question)
            
            if not embedding:
                logger.warning(f"Could not generate embedding for query {query_id}")
                return {"success": False, "error": "Could not generate embedding"}
            
            # Calculate hash
            question_hash = self._calculate_hash(question)
            
            # Update query
            query.question_embedding = embedding
            query.question_hash = question_hash
            
            self.db.commit()
            
            logger.debug(f"Stored embedding and hash for query {query_id}")
            
            return {
                "success": True,
                "embedding_dimension": len(embedding),
                "hash": question_hash
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error storing query embedding: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def get_cache_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring
        
        Args:
            hours: Time window in hours for statistics
        
        Returns:
            Dict with cache statistics
        """
        try:
            cutoff = datetime.now() - timedelta(hours=hours)
            
            # Get total queries in window
            total_queries = self.db.query(NLQQuery).filter(
                NLQQuery.created_at >= cutoff
            ).count()
            
            # Get cached queries
            cached_queries = self.db.query(NLQQuery).filter(
                and_(
                    NLQQuery.created_at >= cutoff,
                    NLQQuery.from_cache == True
                )
            ).count()
            
            # Get queries with embeddings
            queries_with_embeddings = self.db.query(NLQQuery).filter(
                and_(
                    NLQQuery.created_at >= cutoff,
                    NLQQuery.question_embedding.isnot(None)
                )
            ).count()
            
            # Calculate hit rate
            hit_rate = cached_queries / total_queries if total_queries > 0 else 0.0
            
            # Get average similarity for cached queries
            from sqlalchemy import func as sa_func
            avg_similarity = self.db.query(
                sa_func.avg(NLQQuery.cache_similarity)
            ).filter(
                and_(
                    NLQQuery.created_at >= cutoff,
                    NLQQuery.from_cache == True,
                    NLQQuery.cache_similarity.isnot(None)
                )
            ).scalar() or 0.0
            
            stats = {
                "total_queries": total_queries,
                "cached_queries": cached_queries,
                "queries_with_embeddings": queries_with_embeddings,
                "hit_rate": float(hit_rate),
                "average_similarity": float(avg_similarity) if avg_similarity else None,
                "time_window_hours": hours
            }
            
            # Update Prometheus gauge
            nlq_cache_hit_rate.set(hit_rate)
            
            # Validate hit rate
            validation = cache_config.validate_cache_hit_rate(hit_rate)
            stats['validation'] = validation
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting cache statistics: {e}", exc_info=True)
            return {
                "total_queries": 0,
                "cached_queries": 0,
                "queries_with_embeddings": 0,
                "hit_rate": 0.0,
                "error": str(e)
            }
    
    def _calculate_hash(self, question: str) -> str:
        """Calculate SHA256 hash of question"""
        return hashlib.sha256(question.encode('utf-8')).hexdigest()
    
    def _find_exact_match(
        self,
        question_hash: str,
        user_id: Optional[int] = None
    ) -> Optional[NLQQuery]:
        """
        Find exact match by hash (fastest lookup)
        
        Args:
            question_hash: SHA256 hash of question
            user_id: Optional user ID filter
        
        Returns:
            NLQQuery if found, None otherwise
        """
        try:
            cutoff = datetime.now() - timedelta(hours=cache_config.CACHE_TTL_HOURS)
            
            query = self.db.query(NLQQuery).filter(
                and_(
                    NLQQuery.question_hash == question_hash,
                    NLQQuery.created_at >= cutoff,
                    NLQQuery.answer.isnot(None)  # Only return queries with answers
                )
            )
            
            if user_id:
                query = query.filter(NLQQuery.user_id == user_id)
            
            return query.order_by(NLQQuery.created_at.desc()).first()
            
        except Exception as e:
            logger.error(f"Error finding exact match: {e}", exc_info=True)
            return None
    
    def _find_similar_by_embedding(
        self,
        embedding: List[float],
        question_hash: str,
        user_id: Optional[int] = None,
        threshold: float = 0.95
    ) -> Optional[Dict[str, Any]]:
        """
        Find similar query by embedding similarity
        
        Args:
            embedding: Question embedding vector
            question_hash: Hash of question (to exclude exact match)
            user_id: Optional user ID filter
            threshold: Similarity threshold
        
        Returns:
            Dict with cached query and similarity score, or None
        """
        try:
            cutoff = datetime.now() - timedelta(hours=cache_config.CACHE_TTL_HOURS)
            
            # Get last N queries with embeddings (within TTL)
            query = self.db.query(NLQQuery).filter(
                and_(
                    NLQQuery.question_embedding.isnot(None),
                    NLQQuery.created_at >= cutoff,
                    NLQQuery.answer.isnot(None),
                    NLQQuery.question_hash != question_hash  # Exclude exact match
                )
            )
            
            if user_id:
                query = query.filter(NLQQuery.user_id == user_id)
            
            # Limit to last N queries for performance
            candidates = query.order_by(
                NLQQuery.created_at.desc()
            ).limit(cache_config.MAX_QUERIES_TO_CHECK).all()
            
            if not candidates:
                return None
            
            # Calculate similarity for each candidate
            best_match = None
            best_similarity = 0.0
            
            for candidate in candidates:
                if not candidate.question_embedding:
                    continue
                
                similarity = cosine_similarity(embedding, candidate.question_embedding)
                
                if similarity >= threshold and similarity > best_similarity:
                    best_similarity = similarity
                    best_match = candidate
            
            if best_match:
                result = best_match.to_dict()
                result['similarity'] = best_similarity
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding similar query: {e}", exc_info=True)
            return None
    
    def _record_cache_hit(
        self,
        cached_result: Any,
        similarity: float,
        lookup_time_ms: float
    ) -> None:
        """
        Record cache hit metrics
        
        Args:
            cached_result: Cached query result
            similarity: Similarity score
            lookup_time_ms: Lookup time in milliseconds
        """
        try:
            nlq_cache_hits_total.inc()
            nlq_cache_lookup_time_seconds.observe(lookup_time_ms / 1000.0)
            nlq_cache_similarity_score.observe(similarity)
            
            self._update_cache_stats(hit=True)
            
            # Validate performance
            perf_validation = cache_config.validate_performance(
                lookup_time_ms,
                "cache_lookup"
            )
            
            if perf_validation.get('warning'):
                logger.warning(perf_validation['warning'])
            
        except Exception as e:
            logger.error(f"Error recording cache hit: {e}", exc_info=True)
    
    def _update_cache_stats(self, hit: bool = False, miss: bool = False) -> None:
        """Update internal cache statistics"""
        if hit:
            self._cache_stats['hits'] += 1
        if miss:
            self._cache_stats['misses'] += 1
        
        # Update Prometheus hit rate periodically
        total = self._cache_stats['hits'] + self._cache_stats['misses']
        if total > 0 and total % 10 == 0:  # Update every 10 queries
            hit_rate = self._cache_stats['hits'] / total
            nlq_cache_hit_rate.set(hit_rate)

