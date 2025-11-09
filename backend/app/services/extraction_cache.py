"""
Extraction Cache Service

Caches AI model extraction results in Redis to avoid re-processing.
"""

import hashlib
import json
import redis
from typing import Optional, Dict, Any
from datetime import timedelta
from app.core.config import settings


class ExtractionCache:
    """
    Redis-based cache for extraction results.
    
    Uses SHA256 hash of PDF as cache key.
    TTL: 30 days
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize cache service.
        
        Args:
            redis_client: Optional Redis client (creates default if None)
        """
        if redis_client:
            self.redis = redis_client
        else:
            self.redis = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True
            )
        
        self.ttl_days = 30
        self.key_prefix = "extraction:"
    
    def get_pdf_hash(self, pdf_data: bytes) -> str:
        """Calculate SHA256 hash of PDF"""
        return hashlib.sha256(pdf_data).hexdigest()
    
    def get(self, pdf_data: bytes) -> Optional[Dict[str, Any]]:
        """
        Get cached extraction result.
        
        Args:
            pdf_data: PDF bytes
        
        Returns:
            Cached result dict or None if not found
        """
        key = self.key_prefix + self.get_pdf_hash(pdf_data)
        
        cached = self.redis.get(key)
        if cached:
            return json.loads(cached)
        
        return None
    
    def set(self, pdf_data: bytes, result: Dict[str, Any]) -> bool:
        """
        Cache extraction result.
        
        Args:
            pdf_data: PDF bytes
            result: Extraction result to cache
        
        Returns:
            True if cached successfully
        """
        key = self.key_prefix + self.get_pdf_hash(pdf_data)
        ttl = timedelta(days=self.ttl_days)
        
        try:
            self.redis.setex(
                key,
                ttl,
                json.dumps(result, default=str)
            )
            return True
        except:
            return False
    
    def invalidate(self, pdf_data: bytes) -> bool:
        """Delete cache entry"""
        key = self.key_prefix + self.get_pdf_hash(pdf_data)
        return bool(self.redis.delete(key))
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        keys = self.redis.keys(f"{self.key_prefix}*")
        return {
            "total_cached": len(keys),
            "memory_used": self.redis.info()["used_memory"]
        }

