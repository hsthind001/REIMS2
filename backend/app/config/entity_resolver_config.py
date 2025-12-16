"""
Entity Resolver Configuration

Configuration for fuzzy property name matching including
similarity thresholds, caching, and refresh settings.
"""
import os
from typing import Dict, Any


class EntityResolverConfig:
    """
    Configuration for entity resolver service
    
    All parameters are configurable and can be overridden via environment variables.
    """
    
    # Fuzzy Matching Settings
    SIMILARITY_THRESHOLD: float = float(os.getenv('ENTITY_RESOLVER_THRESHOLD', '0.75'))  # 75% similarity
    MIN_CONFIDENCE: float = float(os.getenv('ENTITY_RESOLVER_MIN_CONFIDENCE', '0.75'))  # Minimum confidence
    MAX_MATCHES: int = int(os.getenv('ENTITY_RESOLVER_MAX_MATCHES', '3'))  # Top 3 matches
    TARGET_ACCURACY: float = float(os.getenv('ENTITY_RESOLVER_TARGET_ACCURACY', '0.85'))  # 85% accuracy target
    
    # Performance Targets
    TARGET_MATCHING_TIME_MS: int = int(os.getenv('ENTITY_RESOLVER_TARGET_TIME_MS', '50'))  # <50ms
    
    # Property List Refresh
    REFRESH_INTERVAL_MINUTES: int = int(os.getenv('ENTITY_RESOLVER_REFRESH_INTERVAL', '5'))  # Refresh every 5 minutes
    AUTO_REFRESH_ENABLED: bool = os.getenv('ENTITY_RESOLVER_AUTO_REFRESH', 'true').lower() == 'true'
    
    # Caching Settings
    CACHE_ENABLED: bool = os.getenv('ENTITY_RESOLVER_CACHE_ENABLED', 'true').lower() == 'true'
    CACHE_TTL_MINUTES: int = int(os.getenv('ENTITY_RESOLVER_CACHE_TTL_MINUTES', '30'))  # Cache match results for 30 minutes
    CACHE_MAX_SIZE: int = int(os.getenv('ENTITY_RESOLVER_CACHE_MAX_SIZE', '1000'))  # Max cached queries
    
    # Database Query Settings
    PROPERTY_STATUS_FILTER: str = os.getenv('ENTITY_RESOLVER_PROPERTY_STATUS', 'active')  # Only active properties
    CASE_SENSITIVE: bool = os.getenv('ENTITY_RESOLVER_CASE_SENSITIVE', 'false').lower() == 'true'
    
    # Matching Strategy
    USE_PARTIAL_RATIO: bool = os.getenv('ENTITY_RESOLVER_USE_PARTIAL_RATIO', 'true').lower() == 'true'  # Use partial_ratio
    USE_RATIO: bool = os.getenv('ENTITY_RESOLVER_USE_RATIO', 'true').lower() == 'true'  # Also use ratio
    USE_TOKEN_SORT_RATIO: bool = os.getenv('ENTITY_RESOLVER_USE_TOKEN_SORT', 'false').lower() == 'true'  # Token sort ratio
    
    # Monitoring
    TRACK_ACCURACY: bool = os.getenv('ENTITY_RESOLVER_TRACK_ACCURACY', 'true').lower() == 'true'
    LOG_MATCHES: bool = os.getenv('ENTITY_RESOLVER_LOG_MATCHES', 'false').lower() == 'true'
    
    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """Get all configuration as dictionary"""
        return {
            'similarity_threshold': cls.SIMILARITY_THRESHOLD,
            'min_confidence': cls.MIN_CONFIDENCE,
            'max_matches': cls.MAX_MATCHES,
            'target_accuracy': cls.TARGET_ACCURACY,
            'target_matching_time_ms': cls.TARGET_MATCHING_TIME_MS,
            'refresh_interval_minutes': cls.REFRESH_INTERVAL_MINUTES,
            'auto_refresh_enabled': cls.AUTO_REFRESH_ENABLED,
            'cache_enabled': cls.CACHE_ENABLED,
            'cache_ttl_minutes': cls.CACHE_TTL_MINUTES,
            'cache_max_size': cls.CACHE_MAX_SIZE,
            'property_status_filter': cls.PROPERTY_STATUS_FILTER,
            'case_sensitive': cls.CASE_SENSITIVE,
            'use_partial_ratio': cls.USE_PARTIAL_RATIO,
            'use_ratio': cls.USE_RATIO,
            'use_token_sort_ratio': cls.USE_TOKEN_SORT_RATIO
        }


# Global configuration instance
entity_resolver_config = EntityResolverConfig()

