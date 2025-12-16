"""
Performance Monitoring for RAG Retrieval Service

Tracks latency, query counts, and performance metrics.
"""
import time
import logging
from functools import wraps
from typing import Callable, Any
from prometheus_client import Histogram, Counter, Gauge

logger = logging.getLogger(__name__)

# Prometheus metrics
retrieval_latency = Histogram(
    'rag_retrieval_latency_seconds',
    'RAG retrieval latency by method',
    ['method', 'has_filters', 'result_count'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
)

retrieval_queries_total = Counter(
    'rag_retrieval_queries_total',
    'Total RAG retrieval queries',
    ['method', 'status']
)

enrichment_latency = Histogram(
    'rag_enrichment_latency_seconds',
    'Chunk enrichment latency',
    ['batch_size'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0]
)

cache_hits = Counter(
    'rag_cache_hits_total',
    'Embedding cache hits',
    ['type']
)

cache_misses = Counter(
    'rag_cache_misses_total',
    'Embedding cache misses',
    ['type']
)

active_retrievals = Gauge(
    'rag_active_retrievals',
    'Currently active retrieval operations'
)


def track_retrieval_performance(method: str):
    """
    Decorator to track retrieval performance.
    
    Args:
        method: Retrieval method name ('pinecone', 'postgresql', 'hybrid', etc.)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            active_retrievals.inc()
            
            try:
                # Extract filters from kwargs
                has_filters = bool(
                    kwargs.get('property_id') or
                    kwargs.get('period_id') or
                    kwargs.get('document_type')
                )
                
                # Execute function
                results = func(*args, **kwargs)
                
                # Track success
                retrieval_queries_total.labels(method=method, status='success').inc()
                
                # Record latency
                elapsed = time.time() - start_time
                result_count = len(results) if isinstance(results, list) else 0
                
                retrieval_latency.labels(
                    method=method,
                    has_filters=str(has_filters),
                    result_count=str(result_count)
                ).observe(elapsed)
                
                # Log slow queries
                if elapsed > 2.0:
                    logger.warning(
                        f"Slow retrieval: {method} took {elapsed:.3f}s "
                        f"(filters={has_filters}, results={result_count})"
                    )
                
                return results
                
            except Exception as e:
                # Track failure
                retrieval_queries_total.labels(method=method, status='error').inc()
                logger.error(f"Retrieval failed: {method} - {e}")
                raise
            finally:
                active_retrievals.dec()
        
        return wrapper
    return decorator


def track_enrichment_performance(batch_size: int):
    """
    Decorator to track enrichment performance.
    
    Args:
        batch_size: Number of chunks being enriched
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                elapsed = time.time() - start_time
                enrichment_latency.labels(batch_size=str(batch_size)).observe(elapsed)
                
                return result
            except Exception as e:
                logger.error(f"Enrichment failed: {e}")
                raise
        
        return wrapper
    return decorator


def track_cache_usage(cache_type: str):
    """
    Track cache hit/miss.
    
    Args:
        cache_type: Type of cache ('embedding', 'period', etc.)
    """
    def track_hit():
        cache_hits.labels(type=cache_type).inc()
    
    def track_miss():
        cache_misses.labels(type=cache_type).inc()
    
    return track_hit, track_miss

