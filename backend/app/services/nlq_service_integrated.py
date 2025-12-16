"""
Integrated NLQ Service with Semantic Cache

Integrates SemanticCacheService (Component A) with NaturalLanguageQueryService (Component B)
following the integration requirements:
1. Component A called before Component B
2. If Component A returns cached result, skip Component B
3. Component B updates Component A cache on new queries
4. Error in Component A should not block Component B (graceful degradation)
5. Metrics for cache hit/miss rate
"""
import logging
from typing import Dict, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.nlq_service import NaturalLanguageQueryService
from app.services.semantic_cache_service import SemanticCacheService
from app.config.cache_config import cache_config

# Prometheus metrics
try:
    from prometheus_client import Counter, Gauge, Histogram
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

logger = logging.getLogger(__name__)

# Initialize Prometheus metrics
if PROMETHEUS_AVAILABLE:
    nlq_integration_cache_hits_total = Counter(
        'nlq_integration_cache_hits_total',
        'Total number of cache hits in integrated NLQ service'
    )
    
    nlq_integration_cache_misses_total = Counter(
        'nlq_integration_cache_misses_total',
        'Total number of cache misses in integrated NLQ service'
    )
    
    nlq_integration_cache_error_total = Counter(
        'nlq_integration_cache_error_total',
        'Total number of cache errors (graceful degradation)'
    )
    
    nlq_integration_cache_hit_rate = Gauge(
        'nlq_integration_cache_hit_rate',
        'Cache hit rate for integrated NLQ service (0-1)'
    )
    
    nlq_integration_total_queries = Counter(
        'nlq_integration_total_queries',
        'Total number of queries processed by integrated NLQ service'
    )
    
    nlq_integration_query_latency_seconds = Histogram(
        'nlq_integration_query_latency_seconds',
        'Total query latency including cache lookup',
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
    )
else:
    # Dummy metrics
    class DummyMetric:
        def inc(self, *args, **kwargs): pass
        def set(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
    
    nlq_integration_cache_hits_total = DummyMetric()
    nlq_integration_cache_misses_total = DummyMetric()
    nlq_integration_cache_error_total = DummyMetric()
    nlq_integration_cache_hit_rate = DummyMetric()
    nlq_integration_total_queries = DummyMetric()
    nlq_integration_query_latency_seconds = DummyMetric()


class IntegratedNLQService:
    """
    Integrated NLQ Service with Semantic Cache
    
    Integration Pattern:
    1. Check cache (Component A) first
    2. If cache hit, return cached result (skip Component B)
    3. If cache miss, call Component B (NLQ Service)
    4. Update cache (Component A) with new result
    5. Graceful degradation if cache fails
    """
    
    def __init__(self, db: Session):
        """
        Initialize integrated service
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        
        # Initialize Component A (Semantic Cache)
        self.cache_service = None
        try:
            self.cache_service = SemanticCacheService(db)
            logger.info("✅ SemanticCacheService (Component A) initialized")
        except Exception as e:
            logger.warning(f"⚠️  SemanticCacheService initialization failed: {e}. Will operate without cache.")
            self.cache_service = None
        
        # Initialize Component B (NLQ Service)
        try:
            self.nlq_service = NaturalLanguageQueryService(db)
            logger.info("✅ NaturalLanguageQueryService (Component B) initialized")
        except Exception as e:
            logger.error(f"❌ NaturalLanguageQueryService initialization failed: {e}")
            raise  # NLQ service is critical, fail if it can't be initialized
        
        # Cache statistics
        self._cache_stats = {
            'hits': 0,
            'misses': 0,
            'errors': 0,
            'total': 0
        }
    
    def query(
        self,
        question: str,
        user_id: int,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process natural language query with integrated caching
        
        Flow:
        1. Check semantic cache (Component A)
        2. If cache hit, return cached result (skip Component B)
        3. If cache miss, call NLQ service (Component B)
        4. Update cache with new result (Component A)
        5. Return result
        
        Args:
            question: User's natural language question
            user_id: User ID for logging
            context: Optional context dict with property_id, property_code, property_name
        
        Returns:
            Dict with answer, data, citations, and metadata
        """
        start_time = datetime.now()
        self._cache_stats['total'] += 1
        nlq_integration_total_queries.inc()
        
        logger.info(f"Processing integrated NLQ query: '{question[:50]}...' for user {user_id}")
        
        # STEP 1: Check cache (Component A) - BEFORE Component B
        cached_result = None
        cache_hit = False
        
        if self.cache_service and cache_config.ENABLE_SEMANTIC_CACHE:
            try:
                cached_result = self.cache_service.find_similar_query(
                    question=question,
                    user_id=user_id
                )
                
                if cached_result:
                    cache_hit = True
                    self._cache_stats['hits'] += 1
                    nlq_integration_cache_hits_total.inc()
                    
                    # Calculate latency
                    latency = (datetime.now() - start_time).total_seconds()
                    nlq_integration_query_latency_seconds.observe(latency)
                    
                    # Update hit rate
                    self._update_cache_hit_rate()
                    
                    logger.info(
                        f"✅ Cache HIT for query: '{question[:50]}...' "
                        f"(similarity: {cached_result.get('cache_similarity', 'N/A')}, "
                        f"latency: {latency*1000:.2f}ms)"
                    )
                    
                    # Mark as from cache if query_id exists
                    if 'id' in cached_result:
                        try:
                            from app.models.nlq_query import NLQQuery
                            query_obj = self.db.query(NLQQuery).filter(
                                NLQQuery.id == cached_result['id']
                            ).first()
                            if query_obj:
                                query_obj.from_cache = True
                                if 'similarity' in cached_result:
                                    query_obj.cache_similarity = float(cached_result['similarity']) * 100
                                self.db.commit()
                        except Exception as e:
                            logger.warning(f"Failed to update cache metadata: {e}")
                            self.db.rollback()
                    
                    # Return cached result (SKIP Component B)
                    return {
                        **cached_result,
                        'from_cache': True,
                        'cache_similarity': cached_result.get('cache_similarity', cached_result.get('similarity')),
                        'execution_time_ms': int(latency * 1000)
                    }
                
                else:
                    # Cache miss
                    self._cache_stats['misses'] += 1
                    nlq_integration_cache_misses_total.inc()
                    logger.debug(f"Cache MISS for query: '{question[:50]}...'")
                    
            except Exception as e:
                # GRACEFUL DEGRADATION: Error in Component A should not block Component B
                self._cache_stats['errors'] += 1
                nlq_integration_cache_error_total.inc()
                logger.warning(
                    f"⚠️  Cache lookup failed (graceful degradation): {e}. "
                    f"Proceeding with NLQ service (Component B)."
                )
                # Continue to Component B
        
        # STEP 2: Call Component B (NLQ Service) - only if cache miss
        try:
            nlq_result = self.nlq_service.query(
                question=question,
                user_id=user_id,
                context=context
            )
            
            # Calculate total latency
            latency = (datetime.now() - start_time).total_seconds()
            nlq_integration_query_latency_seconds.observe(latency)
            
            # STEP 3: Update cache (Component A) with new result
            if self.cache_service and cache_config.ENABLE_SEMANTIC_CACHE:
                self._update_cache_with_result(nlq_result, question)
            
            # Update hit rate
            self._update_cache_hit_rate()
            
            # Add metadata
            result = {
                **nlq_result,
                'from_cache': False,
                'execution_time_ms': int(latency * 1000)
            }
            
            logger.info(
                f"✅ NLQ query processed (cache miss): '{question[:50]}...' "
                f"(latency: {latency*1000:.2f}ms)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ NLQ service (Component B) failed: {e}", exc_info=True)
            # Calculate latency even on error
            latency = (datetime.now() - start_time).total_seconds()
            nlq_integration_query_latency_seconds.observe(latency)
            
            return {
                "success": False,
                "error": str(e),
                "question": question,
                "answer": f"❌ Error: {str(e)}",
                "from_cache": False,
                "execution_time_ms": int(latency * 1000)
            }
    
    def _update_cache_with_result(
        self,
        nlq_result: Dict[str, Any],
        question: str
    ) -> None:
        """
        Update Component A cache with new query result from Component B
        
        Args:
            nlq_result: Result from NLQ service
            question: Original question
        """
        if not self.cache_service:
            return
        
        try:
            query_id = nlq_result.get('query_id')
            if query_id:
                # Store query with embedding for future cache hits
                cache_result = self.cache_service.store_query_with_embedding(
                    query_id=query_id,
                    question=question,
                    force_regenerate=False
                )
                
                if cache_result.get('success'):
                    logger.debug(f"✅ Updated cache with query {query_id}")
                else:
                    logger.warning(f"⚠️  Failed to update cache: {cache_result.get('error')}")
                    
        except Exception as e:
            # Non-critical: cache update failure shouldn't break the query
            logger.warning(f"⚠️  Cache update failed (non-critical): {e}")
    
    def _update_cache_hit_rate(self) -> None:
        """Update cache hit rate metric"""
        try:
            total = self._cache_stats['hits'] + self._cache_stats['misses']
            if total > 0:
                hit_rate = self._cache_stats['hits'] / total
                nlq_integration_cache_hit_rate.set(hit_rate)
        except Exception as e:
            logger.debug(f"Failed to update cache hit rate: {e}")
    
    def get_cache_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring
        
        Args:
            hours: Time window in hours
        
        Returns:
            Dict with cache statistics
        """
        stats = {
            'integration_stats': {
                'total_queries': self._cache_stats['total'],
                'cache_hits': self._cache_stats['hits'],
                'cache_misses': self._cache_stats['misses'],
                'cache_errors': self._cache_stats['errors'],
                'hit_rate': (
                    self._cache_stats['hits'] / (self._cache_stats['hits'] + self._cache_stats['misses'])
                    if (self._cache_stats['hits'] + self._cache_stats['misses']) > 0 else 0.0
                )
            }
        }
        
        # Get Component A statistics if available
        if self.cache_service:
            try:
                component_a_stats = self.cache_service.get_cache_statistics(hours=hours)
                stats['component_a_stats'] = component_a_stats
            except Exception as e:
                logger.warning(f"Failed to get Component A statistics: {e}")
                stats['component_a_stats'] = {'error': str(e)}
        
        return stats
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of both components
        
        Returns:
            Dict with health status
        """
        status = {
            'component_a': {
                'name': 'SemanticCacheService',
                'available': self.cache_service is not None,
                'enabled': cache_config.ENABLE_SEMANTIC_CACHE if self.cache_service else False
            },
            'component_b': {
                'name': 'NaturalLanguageQueryService',
                'available': self.nlq_service is not None
            },
            'integration': {
                'status': 'healthy' if (self.cache_service or not cache_config.ENABLE_SEMANTIC_CACHE) and self.nlq_service else 'degraded',
                'graceful_degradation': True  # Always enabled
            }
        }
        
        return status

