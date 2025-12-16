"""
Cache Configuration

Configurable parameters for semantic caching including
similarity threshold, TTL, and performance targets.
"""
from typing import Dict, Any
from app.core.config import settings


class CacheConfig:
    """
    Configuration for semantic caching
    
    All parameters are configurable and can be overridden via environment variables
    or config file.
    """
    
    # Similarity threshold (0.0 to 1.0)
    SIMILARITY_THRESHOLD: float = 0.95  # 95% similarity required for cache hit
    
    # Cache TTL (Time To Live)
    CACHE_TTL_HOURS: int = 24  # 24 hour cache window
    
    # Performance settings
    MAX_QUERIES_TO_CHECK: int = 100  # Limit search space for performance
    PERFORMANCE_TARGET_MS: int = 50  # 50ms lookup target
    
    # Feature flag
    ENABLE_SEMANTIC_CACHE: bool = True  # Enable/disable semantic caching
    
    # Embedding settings
    EMBEDDING_DIMENSION: int = 1536  # OpenAI text-embedding-3-large dimension
    
    # Hash settings
    HASH_ALGORITHM: str = 'sha256'  # Algorithm for question hash
    
    # Monitoring thresholds
    TARGET_CACHE_HIT_RATE: float = 0.30  # Target 30% cache hit rate
    WARNING_CACHE_HIT_RATE: float = 0.20  # Warn if below 20%
    
    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """Get all configuration as dictionary"""
        return {
            'similarity_threshold': cls.SIMILARITY_THRESHOLD,
            'cache_ttl_hours': cls.CACHE_TTL_HOURS,
            'max_queries_to_check': cls.MAX_QUERIES_TO_CHECK,
            'performance_target_ms': cls.PERFORMANCE_TARGET_MS,
            'enable_semantic_cache': cls.ENABLE_SEMANTIC_CACHE,
            'embedding_dimension': cls.EMBEDDING_DIMENSION,
            'target_cache_hit_rate': cls.TARGET_CACHE_HIT_RATE
        }
    
    @classmethod
    def validate_performance(cls, actual_time_ms: float, operation: str) -> Dict[str, Any]:
        """
        Validate performance against targets
        
        Args:
            actual_time_ms: Actual processing time in milliseconds
            operation: Operation name for logging
        
        Returns:
            Dict with validation results
        """
        warning_threshold = cls.PERFORMANCE_TARGET_MS * 2  # Allow 2x margin
        
        result = {
            'operation': operation,
            'actual_time_ms': actual_time_ms,
            'target_time_ms': cls.PERFORMANCE_TARGET_MS,
            'within_target': actual_time_ms <= cls.PERFORMANCE_TARGET_MS,
            'within_warning': actual_time_ms <= warning_threshold,
            'exceeds_warning': actual_time_ms > warning_threshold
        }
        
        if result['exceeds_warning']:
            result['warning'] = f"{operation} took {actual_time_ms:.2f}ms, exceeds warning threshold of {warning_threshold}ms"
        elif not result['within_target']:
            result['warning'] = f"{operation} took {actual_time_ms:.2f}ms, exceeds target of {cls.PERFORMANCE_TARGET_MS}ms"
        else:
            result['warning'] = None
        
        return result
    
    @classmethod
    def validate_cache_hit_rate(cls, hit_rate: float) -> Dict[str, Any]:
        """
        Validate cache hit rate against targets
        
        Args:
            hit_rate: Current cache hit rate (0.0 to 1.0)
        
        Returns:
            Dict with validation results
        """
        result = {
            'hit_rate': hit_rate,
            'target_rate': cls.TARGET_CACHE_HIT_RATE,
            'warning_rate': cls.WARNING_CACHE_HIT_RATE,
            'meets_target': hit_rate >= cls.TARGET_CACHE_HIT_RATE,
            'above_warning': hit_rate >= cls.WARNING_CACHE_HIT_RATE,
            'below_warning': hit_rate < cls.WARNING_CACHE_HIT_RATE
        }
        
        if result['below_warning']:
            result['warning'] = f"Cache hit rate {hit_rate:.1%} is below warning threshold of {cls.WARNING_CACHE_HIT_RATE:.1%}"
        elif not result['meets_target']:
            result['warning'] = f"Cache hit rate {hit_rate:.1%} is below target of {cls.TARGET_CACHE_HIT_RATE:.1%}"
        else:
            result['warning'] = None
        
        return result


# Global configuration instance
cache_config = CacheConfig()

