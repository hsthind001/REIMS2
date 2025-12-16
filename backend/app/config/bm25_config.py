"""
BM25 Configuration

Configurable parameters for BM25 keyword search including
algorithm parameters, cache settings, and performance targets.
"""
import os
from typing import Dict, Any
from pathlib import Path


class BM25Config:
    """
    Configuration for BM25 keyword search
    
    All parameters are configurable and can be overridden via environment variables.
    """
    
    # BM25 Algorithm Parameters
    K1: float = 1.5  # Term frequency saturation parameter
    B: float = 0.75  # Length normalization parameter
    
    # Cache Configuration
    CACHE_DIR: str = os.getenv('BM25_CACHE_DIR', '/tmp/bm25_cache')
    CACHE_FILENAME: str = 'bm25_index.pkl'
    CACHE_VERSION: int = 1  # Increment when index structure changes
    
    # Auto-Rebuild Settings
    AUTO_REBUILD: bool = os.getenv('BM25_AUTO_REBUILD', 'false').lower() == 'true'
    REBUILD_THRESHOLD: int = int(os.getenv('BM25_REBUILD_THRESHOLD', '100'))  # Rebuild when chunk count changes by N
    
    # Performance Settings
    MAX_RESULTS: int = int(os.getenv('BM25_MAX_RESULTS', '100'))  # Maximum results to return
    SEARCH_TIMEOUT_MS: int = int(os.getenv('BM25_SEARCH_TIMEOUT_MS', '100'))  # Target search latency
    
    # Index Building
    BATCH_SIZE: int = int(os.getenv('BM25_BATCH_SIZE', '1000'))  # Chunks per batch during index building
    
    @classmethod
    def get_cache_path(cls) -> Path:
        """Get full path to cache file"""
        cache_dir = Path(cls.CACHE_DIR)
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / cls.CACHE_FILENAME
    
    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """Get all configuration as dictionary"""
        return {
            'k1': cls.K1,
            'b': cls.B,
            'cache_dir': cls.CACHE_DIR,
            'cache_filename': cls.CACHE_FILENAME,
            'cache_version': cls.CACHE_VERSION,
            'auto_rebuild': cls.AUTO_REBUILD,
            'rebuild_threshold': cls.REBUILD_THRESHOLD,
            'max_results': cls.MAX_RESULTS,
            'search_timeout_ms': cls.SEARCH_TIMEOUT_MS,
            'batch_size': cls.BATCH_SIZE
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
        warning_threshold = cls.SEARCH_TIMEOUT_MS * 2  # Allow 2x margin
        
        result = {
            'operation': operation,
            'actual_time_ms': actual_time_ms,
            'target_time_ms': cls.SEARCH_TIMEOUT_MS,
            'within_target': actual_time_ms <= cls.SEARCH_TIMEOUT_MS,
            'within_warning': actual_time_ms <= warning_threshold,
            'exceeds_warning': actual_time_ms > warning_threshold
        }
        
        if result['exceeds_warning']:
            result['warning'] = f"{operation} took {actual_time_ms:.2f}ms, exceeds warning threshold of {warning_threshold}ms"
        elif not result['within_target']:
            result['warning'] = f"{operation} took {actual_time_ms:.2f}ms, exceeds target of {cls.SEARCH_TIMEOUT_MS}ms"
        else:
            result['warning'] = None
        
        return result


# Global configuration instance
bm25_config = BM25Config()

