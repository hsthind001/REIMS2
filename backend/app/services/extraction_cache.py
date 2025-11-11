"""
Extraction Cache Service for REIMS2
Caches AI model results in Redis to avoid re-processing identical documents.

Sprint 2: AI/ML Intelligence Layer
"""
import hashlib
import json
from typing import Optional, Dict, Any
from datetime import timedelta
import redis

from app.core.config import settings


class ExtractionCache:
    """
    Redis-based cache for extraction results.
    
    Features:
    - SHA256 hashing of PDF content
    - 30-day TTL for cached results
    - Automatic cache invalidation
    - Cache hit/miss tracking
    """
    
    # Cache TTL: 30 days
    CACHE_TTL = timedelta(days=30)
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize extraction cache.
        
        Args:
            redis_client: Redis client instance (auto-created if None)
        """
        if redis_client is None:
            self.redis = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=getattr(settings, 'REDIS_DB', 0),
                decode_responses=True
            )
        else:
            self.redis = redis_client
    
    def get_pdf_hash(self, pdf_content: bytes) -> str:
        """
        Calculate SHA256 hash of PDF content for unique identification.
        
        Args:
            pdf_content: Raw PDF bytes
            
        Returns:
            Hex string of SHA256 hash
        """
        return hashlib.sha256(pdf_content).hexdigest()
    
    def get_cache_key(self, pdf_hash: str, document_type: str, engine_names: list) -> str:
        """
        Generate cache key from PDF hash, document type, and engines used.
        
        Args:
            pdf_hash: SHA256 hash of PDF
            document_type: Type of document (balance_sheet, income_statement, etc.)
            engine_names: List of engines used in extraction
            
        Returns:
            Cache key string
        """
        engines_str = '-'.join(sorted(engine_names))
        return f"extraction:{pdf_hash}:{document_type}:{engines_str}"
    
    def get_cached_result(
        self,
        pdf_hash: str,
        document_type: str,
        engine_names: list
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached extraction result.
        
        Args:
            pdf_hash: SHA256 hash of PDF
            document_type: Type of document
            engine_names: List of engines used
            
        Returns:
            Cached result dict or None if cache miss
        """
        try:
            cache_key = self.get_cache_key(pdf_hash, document_type, engine_names)
            cached_data = self.redis.get(cache_key)
            
            if cached_data:
                # Increment cache hit counter
                self.redis.incr(f"stats:cache_hits:{document_type}")
                return json.loads(cached_data)
            else:
                # Increment cache miss counter
                self.redis.incr(f"stats:cache_misses:{document_type}")
                return None
        except Exception as e:
            print(f"Cache retrieval error: {e}")
            return None
    
    def cache_result(
        self,
        pdf_hash: str,
        document_type: str,
        engine_names: list,
        result_data: Dict[str, Any],
        ttl: Optional[timedelta] = None
    ) -> bool:
        """
        Cache extraction result in Redis.
        
        Args:
            pdf_hash: SHA256 hash of PDF
            document_type: Type of document
            engine_names: List of engines used
            result_data: Extraction result to cache
            ttl: Time to live (default: 30 days)
            
        Returns:
            True if cached successfully
        """
        try:
            cache_key = self.get_cache_key(pdf_hash, document_type, engine_names)
            ttl_seconds = int((ttl or self.CACHE_TTL).total_seconds())
            
            # Serialize and cache
            cached_data = json.dumps(result_data, default=str)
            self.redis.setex(cache_key, ttl_seconds, cached_data)
            
            return True
        except Exception as e:
            print(f"Cache storage error: {e}")
            return False
    
    def invalidate_cache(
        self,
        pdf_hash: str,
        document_type: Optional[str] = None
    ) -> int:
        """
        Invalidate cached results for a PDF.
        
        Args:
            pdf_hash: SHA256 hash of PDF
            document_type: Optional filter by document type
            
        Returns:
            Number of cache entries deleted
        """
        try:
            if document_type:
                # Delete specific document type cache
                pattern = f"extraction:{pdf_hash}:{document_type}:*"
            else:
                # Delete all caches for this PDF
                pattern = f"extraction:{pdf_hash}:*"
            
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            print(f"Cache invalidation error: {e}")
            return 0
    
    def get_cache_statistics(self, document_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get cache hit/miss statistics.
        
        Args:
            document_type: Optional filter by document type
            
        Returns:
            Dict with cache statistics
        """
        try:
            if document_type:
                hits = int(self.redis.get(f"stats:cache_hits:{document_type}") or 0)
                misses = int(self.redis.get(f"stats:cache_misses:{document_type}") or 0)
            else:
                # Aggregate across all document types
                hit_keys = self.redis.keys("stats:cache_hits:*")
                miss_keys = self.redis.keys("stats:cache_misses:*")
                
                hits = sum(int(self.redis.get(k) or 0) for k in hit_keys)
                misses = sum(int(self.redis.get(k) or 0) for k in miss_keys)
            
            total = hits + misses
            hit_rate = (hits / total * 100) if total > 0 else 0
            
            return {
                'cache_hits': hits,
                'cache_misses': misses,
                'total_requests': total,
                'hit_rate_percentage': round(hit_rate, 2),
                'document_type': document_type or 'all'
            }
        except Exception as e:
            return {
                'error': str(e),
                'cache_hits': 0,
                'cache_misses': 0
            }
    
    def clear_all_cache(self) -> int:
        """
        Clear all extraction cache entries.
        
        Warning: Use with caution in production!
        
        Returns:
            Number of cache entries deleted
        """
        try:
            keys = self.redis.keys("extraction:*")
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            print(f"Cache clear error: {e}")
            return 0
